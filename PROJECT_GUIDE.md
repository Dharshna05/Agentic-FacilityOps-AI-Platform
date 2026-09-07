# PROJECT_GUIDE — Infosys Agentic AI for Smart Facility Operations and Optimization

This is the single reference document for this repository: how to run it, what every
file does and why it exists, the full tech stack, where every dataset came from, and
honest ML metrics for every model. It replaces the older scattered docs (README,
HOW_TO_RUN, TECH_STACK_AND_DATA_SOURCES, DATASET_REQUEST, DOCUMENTATION_TASK,
TEAM_TASKS, UI_REBUILD_NOTES) — those were superseded and removed to avoid duplicate,
drifting copies of the same information.

**Scope: all 4 milestones implemented** — Energy, Maintenance, Occupancy, and Security,
each with a real trained ML model (several with more than one model, honestly compared),
a genuinely agentic tool-calling layer, real cross-agent handoffs written to the
database, and a full dashboard. 42/42 backend tests passing, frontend builds clean.

---

## 1. How to run

### Backend
```bash
cd backend
py -3.13 -m venv venv          # or -3.12 — TensorFlow needs 3.12/3.13, not 3.14
venv\Scripts\Activate.ps1      # Windows PowerShell. macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env         # macOS/Linux: cp .env.example .env
python -m uvicorn app.main:app --reload
# -> http://localhost:8000/docs   (Swagger UI)
# Data auto-ingests on first startup.
```
> **Windows note:** if `uvicorn app.main:app --reload` fails with an "Application
> Control policy has blocked this file" error, `python -m uvicorn app.main:app --reload`
> (as above) routes through `python.exe` instead of the blocked `uvicorn.exe`
> entrypoint — same fix applies to other pip-installed `.exe` tools.

### Frontend (separate terminal)
```bash
cd frontend
npm install
npm run dev
# -> http://localhost:5173/energy | /maintenance | /occupancy | /security
```

### Docker (one command, full stack)
```bash
docker-compose up --build
```

### Tests
```bash
cd backend
python -m pytest tests/ -v      # expect 42 passed
```

### Bring your own dataset
Every dashboard has an **Upload Dataset** button (CSV or Excel). Column names are
auto-detected under common aliases (e.g. `zone`/`zone_id`/`room_id` all map to the same
field) — no reformatting needed. Uploading replaces that milestone's readings and every
KPI, chart, and model score recomputes from the new data; there's nothing hardcoded
downstream of the database. Each dashboard also has a **Manage Dataset** panel to
add, view, or delete individual records by hand, and clicking an entity in a chart
(e.g. an access point in the Security heatmap) opens that panel pre-filtered to it.

### Using a real LLM instead of the mock provider
`AI_PROVIDER=mock` in `backend/.env` by default — deterministic, no API key needed.
For real agentic tool-calling:
```
AI_PROVIDER=groq
GROQ_API_KEY=your_key_here   # free at https://console.groq.com/keys
```
`AI_PROVIDER=gemini` + `GEMINI_API_KEY` also works. If the configured provider's key is
missing or a live call fails (bad key, rate limit, network issue), the app falls back to
the mock provider gracefully instead of crashing the request — the response's `provider`
field always reflects what actually ran.

---

## 2. Tech stack

### Backend
| Technology | Why |
|---|---|
| Python 3.12/3.13 | One language for both the web API and ML — no separate ML microservice |
| FastAPI | Async HTTP framework, auto Swagger docs at `/docs`, Pydantic request/response validation |
| SQLAlchemy (ORM) | DB tables as Python classes, queried without raw SQL |
| SQLite (WAL mode) | Zero-setup dev database; WAL + widened connection pool so concurrent dashboard polling/writes don't lock or exhaust connections; swappable for Postgres via one connection string |
| pandas / NumPy | All tabular data manipulation and numerics underlying the ML pipelines |
| scikit-learn | Every trained model: Linear/Logistic Regression, Random Forest, Gradient/Hist Gradient Boosting, Isolation Forest, Local Outlier Factor |
| TensorFlow / Keras | The Conv1D CNN (Occupancy's supplementary trend model) |
| joblib | Serializes trained models to `.pkl` so the API loads once and reuses across requests |
| python-dotenv | Loads `backend/.env` into environment variables |
| Groq SDK / google-genai SDK | Real LLM tool-calling providers for the agentic layer |
| pytest + httpx/TestClient | Backend test suite, no running server needed |

### Frontend
| Technology | Why |
|---|---|
| React 18 | Functional components + hooks throughout |
| Vite | Dev server + production bundler |
| React Router v6 | Client-side routing between the 4 dashboards |
| Tailwind CSS | Utility-first styling from one design-token config |
| Recharts | Consumption/breakdown charts, ML reliability scatter plots |
| Framer Motion | Slide-in panels (dataset manager, upload panel, detail drawers) |
| Axios | HTTP calls to the FastAPI backend |
| Custom SVG (no library) | Fleet Health Radar, Agent Trace Viewer, zone/risk heatmaps — layouts no off-the-shelf chart library supports directly |

### Infra
Docker + Docker Compose (optional one-command full-stack run), Git/GitHub.

---

## 3. Repository structure — what every file does

```
facilityops-handout/
├── backend/
│   ├── app/
│   │   ├── main.py                        FastAPI app entrypoint. Wires up CORS, the
│   │   │                                   crash-safety middleware (catches ANY
│   │   │                                   unhandled exception INSIDE CORSMiddleware
│   │   │                                   so the browser always gets a real, readable
│   │   │                                   error instead of a bare "Network Error"),
│   │   │                                   DB init, and all 4 routers.
│   │   ├── core/
│   │   │   ├── config.py                  Settings loaded from .env (AI_PROVIDER, API
│   │   │   │                              keys, DB URL, CORS origins).
│   │   │   ├── database.py                SQLAlchemy engine/session setup. WAL mode +
│   │   │   │                              busy_timeout + widened connection pool so
│   │   │   │                              concurrent dashboard traffic doesn't lock or
│   │   │   │                              exhaust connections.
│   │   │   ├── intelligence_engine.py     LLM-facing layer: builds prompts from each
│   │   │   │                              agent's analysis, calls the configured
│   │   │   │                              provider, and safely falls back to the mock
│   │   │   │                              provider if a real API call fails at runtime
│   │   │   │                              (_safe_generate / _safe_agentic_task).
│   │   │   ├── agent_tools.py             Tool functions the Energy Agent's LLM can
│   │   │   │                              call (consumption summary, anomaly check,
│   │   │   │                              forecast, maintenance handoff, etc).
│   │   │   ├── maintenance_tools.py       Same idea, for the Maintenance Agent.
│   │   │   ├── occupancy_tools.py         Same idea, for the Occupancy Agent (includes
│   │   │   │                              the restricted-zone → Security handoff tool).
│   │   │   └── security_tools.py          Same idea, for the Security Agent.
│   │   ├── agents/
│   │   │   ├── energy_agent.py            init → analyze() → recommend() → run()
│   │   │   │                              template. Rule-based efficiency
│   │   │   │                              recommendations from real consumption
│   │   │   │                              analytics.
│   │   │   ├── maintenance_agent.py       Same template — scores fleet health from the
│   │   │   │                              trained RUL model, ranks maintenance alerts.
│   │   │   ├── occupancy_agent.py         Same template — scores zone occupancy,
│   │   │   │                              flags restricted-zone activity to Security.
│   │   │   └── security_agent.py          Same template — scores access-event anomaly
│   │   │                                   risk, opens alerts above the risk bar.
│   │   ├── api/
│   │   │   ├── routes.py                  All /energy/* endpoints: ingest, upload,
│   │   │   │                              dashboard, forecast, model comparison,
│   │   │   │                              briefing, investigate, manual record CRUD.
│   │   │   ├── maintenance_routes.py      All /maintenance/* endpoints, same shape.
│   │   │   ├── occupancy_routes.py        All /occupancy/* endpoints, same shape.
│   │   │   └── security_routes.py         All /security/* endpoints, same shape.
│   │   ├── models/                        SQLAlchemy table definitions, one file per
│   │   │                                  domain (energy/maintenance/occupancy/
│   │   │                                  security _models.py) + schemas.py for
│   │   │                                  Pydantic request/response shapes.
│   │   ├── services/
│   │   │   ├── data_service.py            Energy CSV ingestion + flexible external-
│   │   │   │                              column mapping.
│   │   │   ├── maintenance_service.py     Fleet data access, work-order handling.
│   │   │   ├── occupancy_service.py       Zone data access.
│   │   │   ├── occupancy_cnn_service.py   Loads the trained CNN, runs live inference
│   │   │   │                              on real held-out windows.
│   │   │   ├── security_service.py        Access-point/event data access, alerts.
│   │   │   ├── forecast_service.py        Loads the trained per-horizon forecast
│   │   │   │                              models, serves predictions + honest
│   │   │   │                              per-horizon and per-model accuracy.
│   │   │   ├── health_service.py          Loads the trained RUL model, scores assets.
│   │   │   └── ai_providers/              base.py (interface) + factory.py (picks
│   │   │                                  provider from AI_PROVIDER) + mock_provider.py
│   │   │                                  / groq_provider.py / gemini_provider.py
│   │   │                                  (the 3 interchangeable LLM backends) +
│   │   │                                  tool_schema.py (converts Python tool
│   │   │                                  functions to the LLM function-calling schema).
│   │   └── utils/
│   │       ├── energy_analytics.py        Consumption analytics: breakdowns, trend,
│   │       │                              anomaly z-scores, temp/occupancy correlation.
│   │       ├── maintenance_analytics.py   Fleet health scoring, alert generation.
│   │       ├── rul_features.py            Rolling-window feature engineering for the
│   │       │                              RUL model (documents the window-size tuning).
│   │       ├── occupancy_analytics.py     Zone status scoring, heatmap data, AI
│   │       │                              insights, model-confidence readers.
│   │       ├── security_analytics.py      Event scoring (Isolation Forest), risk
│   │       │                              heatmap, access-point activity stats, both
│   │       │                              models' confidence readers.
│   │       └── csv_upload.py              Shared "bring your own dataset" utility —
│   │                                      flexible column-alias resolution used by
│   │                                      every domain's /ingest/upload endpoint.
│   ├── ml_models/
│   │   ├── energy/train_forecast_model.py           Trains + compares 3 models
│   │   │                                             (Linear/RF/GB) per horizon
│   │   │                                             (1h/6h/24h), picks the best by
│   │   │                                             held-out MAE, saves all 3's
│   │   │                                             metrics + the winner's .pkl.
│   │   ├── maintenance/train_health_model.py         Trains + compares 4 regressors
│   │   │                                             for RUL, blends the top
│   │   │                                             performers into an ensemble,
│   │   │                                             also trains quantile models for
│   │   │                                             prediction intervals.
│   │   ├── occupancy/train_occupancy_model.py        Trains + compares 4 classifiers
│   │   │                                             (LogReg/RF/GB/HistGB) for
│   │   │                                             real-time occupancy detection.
│   │   ├── occupancy/train_occupancy_cnn.py          Trains the supplementary Conv1D
│   │   │                                             CNN on 10-minute trend windows.
│   │   └── security/train_anomaly_model.py           Trains Isolation Forest
│   │                                                  (production live scorer) AND
│   │                                                  Local Outlier Factor (honest
│   │                                                  comparison model), evaluated
│   │                                                  identically against injected
│   │                                                  synthetic ground truth.
│   ├── data/
│   │   ├── build_dataset.py                          Builds the Energy raw CSV from 3
│   │   │                                              real public sources.
│   │   ├── build_maintenance_dataset.py               Relabels NASA C-MAPSS onto a
│   │   │                                              fictional facility fleet.
│   │   ├── build_occupancy_dataset.py                 Builds the multi-zone occupancy
│   │   │                                              fleet from the UCI dataset.
│   │   ├── build_security_dataset.py                  Generates the synthetic
│   │   │                                              access-event dataset with
│   │   │                                              injected, labeled anomalies.
│   │   ├── raw/, raw_maintenance/, processed/          The actual dataset files.
│   ├── tests/                                          42 pytest tests across all 4
│   │                                                    domains — ingestion, analytics
│   │                                                    shape, ML endpoints, agentic
│   │                                                    investigation, cross-agent
│   │                                                    handoffs.
│   ├── requirements.txt                                Pinned Python dependencies.
│   └── .env.example                                    Template for AI_PROVIDER / API
│                                                        keys / DATABASE_URL.
│
└── frontend/
    └── src/
        ├── App.jsx                         Route definitions for the 4 dashboards.
        ├── pages/{energy,maintenance,occupancy,security}/*DashboardPage.jsx
        │                                   Top-level page per milestone — fetches
        │                                   data, wires every section together,
        │                                   holds the Upload/Manage Dataset panel state.
        ├── components/
        │   ├── shell/AppShell.jsx          Sidebar navigation + theme toggle.
        │   ├── shared/DataManagerModal.jsx Reusable add/view/delete panel for a
        │   │                              milestone's raw dataset — the same
        │   │                              component powers all 4 dashboards.
        │   ├── shared/DatasetUploadPanel.jsx Reusable drag-drop CSV/Excel upload
        │   │                              panel — same component powers all 4.
        │   ├── energy/                     Consumption/breakdown charts, forecast
        │   │                              card, model comparison panel.
        │   ├── maintenance/                Fleet Health Radar, Asset Table/Detail
        │   │                              Panel, Work Orders panel.
        │   ├── occupancy/                  Zone Heatmap, Zone Detail Panel, CNN
        │   │                              Model Panel (training curves, confusion
        │   │                              matrix, live inference demo).
        │   ├── security/                   Risk Heatmap, Access Point Risk Grid,
        │   │                              Flagged Events list, Model Comparison
        │   │                              panel (Isolation Forest vs LOF).
        │   ├── agent/AgentInvestigationPanel.jsx + AgentTraceViewer.jsx
        │   │                              Shared "Ask the Agent" UI + the live
        │   │                              tool-call trace visualization — same
        │   │                              components power all 4 dashboards.
        │   └── charts/, cards/, ui/         Generic chart/card/header primitives
        │                                   reused across dashboards.
        └── services/*Service.js            One file per domain — every backend
                                            call (dashboard fetch, ingest, upload,
                                            record CRUD, investigate) as a typed
                                            function the pages call.
```

---

## 4. Data sources — where every dataset came from

All 4 modules use **real public data** as their foundation, with any synthetic step
disclosed explicitly rather than presented as real.

| Module | Real source(s) | Honesty note |
|---|---|---|
| **Energy** | PJM Interconnection hourly grid load (2002–2018) + Environment Canada hourly weather (2012) + UCI Occupancy Detection (Candanedo, 2016) | Three real datasets stitched onto one shared 15-min timeline — they don't share an actual overlapping real-world recording period. Submeter split (HVAC/Lighting/Plug/Other) derived from the real total via standard load-share ratios, not independently measured. |
| **Maintenance** | NASA C-MAPSS Turbofan Engine Degradation Simulation, FD001 (Saxena & Goebel, 2008) | Real aircraft-engine sensor values and degradation trajectories, run to actual failure. Sensor names and asset identities relabeled onto fictional facility equipment (e.g. "sensor 11" → `vibration_index`) — disclosed, not hidden. |
| **Occupancy** | UCI Occupancy Detection Data Set (Candanedo & Feldheim, 2016) | Real minute-level ambient sensor data with photo-verified ground truth. The 8-zone live dashboard projects this dataset's real day-of-week/time-of-day profile onto each zone with independent noise — a disclosed synthetic step. |
| **Security** | No real, license-clear public access-control dataset exists | Fully synthetic, explicitly disclosed. Realistic statistical structure (business-hours traffic, per-door risk profiles) with deliberately injected, labeled anomalies so detection can be evaluated honestly. |

Every domain also accepts your own CSV/Excel via the dashboard's **Upload Dataset**
panel or `POST /{domain}/ingest/upload` — see §1.

---

## 5. ML models — honest, current metrics

| Module | Models trained & compared | Winner | Held-out metric |
|---|---|---|---|
| Energy (per horizon: 1h/6h/24h) | Linear Regression, Random Forest, Gradient Boosting | Best picked per horizon by MAE | 1h/6h strong (well above naive baseline); 24h only marginally better — reported honestly, not hidden. See `GET /energy/forecast/model-comparison?horizon=` for exact current numbers. |
| Maintenance (RUL) | Linear Regression, Random Forest, Gradient Boosting, Hist Gradient Boosting, + blended ensemble | Ensemble blend | MAE ~12–15 cycles vs. ~35-cycle naive baseline, evaluated on NASA's own 100 held-out test engines. Quantile models ship an 80% prediction interval alongside every point estimate. |
| Occupancy (real-time) | Logistic Regression, Random Forest, Gradient Boosting, Hist Gradient Boosting | Logistic Regression | ~98% held-out accuracy on UCI's own official test split. |
| Occupancy (10-min trend, supplementary) | Conv1D CNN | — | Reported alongside the primary model with its own honest accuracy/precision/recall/F1/confusion matrix — not claimed to be "better," since it answers a different question (trend vs. snapshot). |
| Security (anomaly detection) | Isolation Forest (unsupervised), Local Outlier Factor (unsupervised) | Isolation Forest | F1 ≈ 0.48 (Isolation Forest) vs ≈ 0.24 (LOF) on the same injected-anomaly ground truth. LOF can't score a new live event without being refit, so Isolation Forest is the production real-time scorer; LOF is kept as a genuine, honestly-reported second opinion. |

Exact current numbers for any model: the corresponding `ml_models/<domain>/model_metrics.json`
(and `lof_model_metrics.json` for Security's comparison model), or the live API —
`GET /security/building`, `GET /occupancy/building`, `GET /energy/forecast/model-comparison`,
`GET /maintenance/fleet` all include current model-confidence fields.

**Re-training after uploading your own dataset:** uploading via the dashboard replaces
the *readings* used for live scoring/analytics immediately — no retraining needed for
the agents' day-to-day numbers. To also retrain a model itself on new data (e.g. after
swapping in a materially different dataset), re-run the relevant script in
`ml_models/<domain>/train_*.py` against your new data.

---

## 6. Architecture: agents, tools, and cross-agent handoffs

Every agent follows the same four-step template: `__init__` (load config/data) →
`analyze()` (score current state with the trained ML model) → `recommend()` (turn that
into ranked alerts) → `run()` (single entrypoint used by the API and by other agents).

Each agent also has a genuinely agentic layer (`GET /<domain>/investigate`): the LLM is
given real tool functions — not pre-computed answers — and decides for itself which to
call, in what order, and whether to act on what it finds. The full tool-call trace is
returned and rendered live in the dashboard's Agent Trace panel.

Two real cross-agent handoffs exist, both writing an actual database row (not just a
log line):
- **Energy → Maintenance**: `flag_for_maintenance_review` opens a real work order,
  tagged `source="energy_agent"`.
- **Occupancy → Security**: `flag_restricted_zone_for_security_review` opens a real
  security alert, tagged `source="occupancy_agent"`, when a restricted zone shows any
  occupancy at all.

---

## 7. Reliability notes (backend)

- **CORS-safe crash handling**: a custom middleware in `app/main.py` catches any
  unhandled exception from inside CORSMiddleware's wrapping, so the browser always gets
  a real, readable JSON error — not a misleading generic "Network Error" — regardless of
  which endpoint fails.
- **AI-provider runtime fallback**: if `AI_PROVIDER=groq`/`gemini` and the live API call
  fails (bad key, rate limit, network issue), the request falls back to the mock
  provider instead of crashing; the response's `provider` field always says what
  actually ran.
- **SQLite concurrency**: WAL journal mode + `busy_timeout` + a widened connection pool
  (20 base / 20 overflow) so multiple dashboards polling simultaneously, plus manual
  add/delete/upload actions layered on top, don't lock the database or exhaust the
  connection pool. Stress-tested at 120 concurrent mixed read/write requests with zero
  failures.

---

## Contributors

| Name | Role |
|---|---|
| Aryan Goswami | Architecture, ML pipelines, agentic AI layer, backend/frontend integration, reliability hardening |
| Dharshna | Frontend & dashboard UI, theme system, agent trace visualization |
| Ramya Sri | Data pipelines, analytics engine, testing, documentation |

## License

MIT — see `LICENSE`.
