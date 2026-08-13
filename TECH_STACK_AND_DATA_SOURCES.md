# Tech Stack & Data Sources — Agentic FacilityOps AI Platform

This document lists every technology used in the project, exactly where it's used, and
where every dataset came from. Written for the project report / viva — use this directly
when explaining "why did you pick X".

---

## 1. Tech Stack

### Backend

| Technology | Where it's used | Why |
|---|---|---|
| **Python 3.12** | Entire backend | Best ecosystem for both web APIs and ML in one language — no separate ML microservice needed. |
| **FastAPI** | `backend/app/main.py`, `app/api/routes.py`, `app/api/maintenance_routes.py` | Async Python web framework. Auto-generates OpenAPI docs at `/docs`, built-in request validation via Pydantic — used for all HTTP endpoints (`/api/energy/*`, `/api/maintenance/*`). |
| **Pydantic** | `app/models/schemas.py` | Request/response validation and serialization for FastAPI endpoints. |
| **SQLAlchemy (ORM)** | `app/core/database.py`, `app/models/energy_models.py`, `app/models/maintenance_models.py` | Defines DB tables as Python classes (`EnergyReading`, `Asset`, `AssetReading`, `MaintenanceEvent`) and queries them without raw SQL. |
| **SQLite** | `backend/energy.db` (created at runtime) | Dev/demo database — file-based, zero setup. Swappable for PostgreSQL in production by changing one connection string in `config.py`; nothing else in the codebase would need to change. |
| **pandas** | `app/utils/energy_analytics.py`, `app/utils/maintenance_analytics.py`, `app/services/data_service.py`, `app/services/maintenance_service.py`, all `ml_models/*/train_*.py` scripts | All tabular data manipulation — reading CSVs, rolling averages, groupby aggregations, joins. |
| **NumPy** | `app/utils/maintenance_analytics.py` (trend slope via `np.polyfit`), ML training scripts | Numerical operations underlying pandas/sklearn. |
| **scikit-learn** | `ml_models/energy/train_forecast_model.py`, `ml_models/maintenance/train_health_model.py` | All ML models: `LinearRegression`, `RandomForestRegressor`, `GradientBoostingRegressor`, plus `TimeSeriesSplit` cross-validation and evaluation metrics (MAE, R², MAPE). |
| **joblib** | Same training scripts + `forecast_service.py`, `health_service.py` | Serializes trained sklearn models to `.pkl` files so the API loads them once and reuses them across requests instead of retraining. |
| **python-dotenv** | `app/core/config.py` | Loads `backend/.env` (API keys, `AI_PROVIDER` setting) into environment variables. |
| **Groq SDK (OpenAI-compatible)** | `app/services/ai_providers/groq_provider.py` | Real LLM provider for the agentic layer — implements actual function-calling (the LLM decides which tools to call) using `llama-3.3-70b-versatile`. |
| **google-genai SDK** | `app/services/ai_providers/gemini_provider.py` | Secondary real LLM provider option (Gemini), same agentic interface as Groq. |
| **pytest** | `backend/tests/test_energy.py`, `backend/tests/test_maintenance.py` | Backend test suite — 24 tests total, run via `pytest tests/ -v`. |
| **httpx / FastAPI TestClient** | Same test files | Sends real HTTP requests to the FastAPI app in tests, without needing a running server. |

### Frontend

| Technology | Where it's used | Why |
|---|---|---|
| **React 18** | Entire `frontend/src/` | Component-based UI; used with functional components + hooks throughout (no class components). |
| **Vite** | Build tool (`vite.config.js`) | Dev server + production bundler — much faster rebuilds than Create React App during development. |
| **React Router v6** | `App.jsx`, `components/shell/AppShell.jsx` | Client-side routing between `/energy` and `/maintenance` without a full page reload; powers the sidebar nav's active-link highlighting. |
| **Tailwind CSS** | `tailwind.config.js` + `className` on every component | Utility-first CSS — all the design tokens (graphite/teal/navy/signal colors, Space Grotesk/Inter/JetBrains Mono fonts) are defined once in `tailwind.config.js` and reused everywhere via class names, instead of writing separate CSS files per component. |
| **Recharts** | `components/charts/ConsumptionChart.jsx`, `BreakdownChart.jsx`, `ModelReliabilityChart.jsx` | All charts: the energy consumption line chart, the submeter breakdown bars, and the actual-vs-predicted ML reliability scatter plots. |
| **Axios** | `services/energyService.js`, `services/maintenanceService.js` | HTTP client for calling the FastAPI backend from the browser. |
| **Custom SVG (no library)** | `components/maintenance/FleetHealthRadar.jsx`, `components/agent/AgentTraceViewer.jsx` | Hand-built radial chart and agent trace visualization — these needed layouts no off-the-shelf chart library supports directly (points arranged on a circle by health score; a live-revealing numbered trace), so they're raw SVG driven by React state. |

### Infrastructure / Tooling

| Technology | Where it's used | Why |
|---|---|---|
| **Docker + Docker Compose** | `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile` | Lets the whole stack (backend + frontend) run identically on any machine with one command, without each teammate manually installing Python/Node versions. |
| **Git / GitHub** | Whole repo | Version control, collaboration, and where the code is submitted from. |

---

## 2. Where Every Dataset Came From

Both datasets are **real public data**, not synthetic/generated. Full detail is in each
module's code, but here's the consolidated list:

### Energy Module (Milestone 1)

Built by merging **three independent real public datasets** onto one shared timeline
(they don't overlap in real time — documented as a deliberate, disclosed choice, not a
single continuous sensor recording):

| Component | Real source | Link |
|---|---|---|
| Power Consumption | PJM Interconnection hourly grid load (2002–2018), rescaled from grid MW to facility kWh | github.com/archd3sai/Hourly-Energy-Consumption-Prediction |
| Outdoor Temperature | Environment Canada hourly weather station data, full year 2012 | github.com/raunak274/analyzing-weather-dataset |
| Occupancy | UCI "Occupancy Detection" dataset (Candanedo, 2016) — real minute-level office sensor data | archive.ics.uci.edu/dataset/357 (mirrored at github.com/mabdullahsoyturk/Occupancy-Detection) |

Submeter shares (HVAC 40% / Lighting 20% / Plug 25% / Other 15%) are derived from the
real total using standard commercial building load-share ratios — not independently
measured, and documented as such.

Build script: `backend/data/build_dataset.py`

### Maintenance Module (Milestone 2)

| Component | Real source | Link |
|---|---|---|
| Equipment sensor degradation data | NASA C-MAPSS Turbofan Engine Degradation Simulation, FD001 subset (Saxena & Goebel, 2008) — real aircraft engines run to actual mechanical failure | github.com/edwardzjl/CMAPSSData (mirror of NASA's official Prognostics Data Repository) |

8 of the 21 real sensor channels (the ones with actual variance in FD001) are relabeled
onto generic facility-equipment sensor names (temperature, pressure, vibration index,
flow rate, efficiency ratio, bleed load) and mapped onto a synthetic facility asset fleet
(chillers, AHUs, pumps, compressors, etc.) — see the full honesty caveat in
`backend/data/build_maintenance_dataset.py`'s docstring and in `README.md`.

Build script: `backend/data/build_maintenance_dataset.py`

### Why real datasets instead of fully synthetic/random data?

A model trained on random/synthetic noise can't demonstrate real predictive skill — it
has nothing genuine to learn. Both modules use real physical measurements (utility grid
load, real weather, real occupancy sensors, real engine-to-failure sensor trajectories)
specifically so the ML models' reported accuracy numbers (e.g. "57.5% better than naive
baseline" for the maintenance model) reflect a model that learned something true about
how machines actually degrade or how buildings actually consume power — not an
artifact of a made-up data-generating process.
