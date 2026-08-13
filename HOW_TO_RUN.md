# How to Run — Agentic FacilityOps AI Platform (Milestone 2)

Every command below was actually executed against this exact codebase before this file
was written (`npm install`, `npm run build`, `pip install -r requirements.txt`,
`pytest tests/ -v` — 24/24 passing). Not copied from a template.

---

## 1. Tech Stack

### Backend
| Tech | Version (pinned) | Role |
|---|---|---|
| Python | 3.12 | Runtime |
| FastAPI | — | HTTP API (`/api/energy/*`, `/maintenance/*`), auto Swagger docs at `/docs` |
| Pydantic | — | Request/response validation |
| SQLAlchemy | — | ORM over SQLite (`EnergyReading`, `Asset`, `AssetReading`, `MaintenanceEvent`) |
| SQLite | — | Dev database, file-based, zero setup |
| pandas / NumPy | pandas 3.0.2, numpy 2.4.4 | Tabular data + numerics for analytics and ML feature prep |
| scikit-learn | 1.8.0 | Trained models: Linear Regression, Random Forest, Gradient Boosting |
| joblib | — | Serializes trained models to `.pkl` so the API loads once and reuses |
| Groq SDK | — | Real LLM tool-calling provider (`llama-3.3-70b-versatile`) for the agentic layer |
| google-genai SDK | — | Alternate real LLM provider (Gemini) |
| pytest + httpx/TestClient | — | 24 backend tests, no server needed to run them |

> **Pinned-version note:** `requirements.txt` is pinned to scikit-learn 1.8.0 / numpy
> 2.4.4 / pandas 3.0.2 on purpose — the shipped `.pkl` model files were trained under
> those exact versions. Installing older/newer versions still runs, but scikit-learn
> will print an `InconsistentVersionWarning` on load. If you ever need different
> versions locally, either retrain (`python ml_models/maintenance/train_health_model.py`
> and the energy equivalent) or keep a dedicated venv per teammate rather than editing
> this file.

### Frontend
| Tech | Role |
|---|---|
| React 18 | UI, functional components + hooks |
| Vite | Dev server + production bundler |
| React Router v6 | `/energy` ⇄ `/maintenance` client-side routing |
| Tailwind CSS | All styling via design tokens in `tailwind.config.js` |
| Recharts | Consumption chart, breakdown chart, ML reliability scatter charts |
| Axios | HTTP calls to the FastAPI backend |
| Custom SVG (no library) | Fleet Health Radar, Agent Trace Viewer |

### Infra
Docker + Docker Compose (optional, one-command full-stack run), Git/GitHub.

---

## 2. Run Locally (recommended for development)

**Backend**
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload
# -> http://localhost:8000/docs   (Swagger UI)
# Data auto-ingests on first startup.
```
> **Windows note (verified):** if `uvicorn app.main:app --reload` fails with an
> "Application Control policy has blocked this file" error, use
> `python -m uvicorn app.main:app --reload` (as above) — this routes through
> `python.exe` instead of the blocked `uvicorn.exe` entrypoint.

**Frontend** (separate terminal)
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
# -> http://localhost:5173/energy
# -> http://localhost:5173/maintenance
```

**Production build check** (what CI/the professor's machine would run):
```bash
cd frontend
npm run build     # outputs frontend/dist — verified clean, 0 errors
```

---

## 3. Run with Docker (one command, full stack)
```bash
docker-compose up --build
# backend  -> http://localhost:8000/docs
# frontend -> http://localhost:5173
```

---

## 4. Run the Tests
```bash
cd backend
python -m pytest tests/ -v
```
Expected: **24 passed** (13 Milestone 1 + 11 Milestone 2). The Milestone-2-critical one
is `test_cross_agent_handoff_creates_real_work_order` — it verifies the Energy →
Maintenance handoff writes an actual database row, not just a log line.

---

## 5. Using a Real LLM Instead of the Mock Provider
By default `AI_PROVIDER=mock` in `backend/.env` — no API key needed, fully deterministic.
To get real agentic tool-calling:
```
AI_PROVIDER=groq
GROQ_API_KEY=your_key_here   # free at https://console.groq.com/keys
```
Everything else (endpoints, frontend, Agent Trace Viewer) is unchanged — only the
`provider` field in the response and the actual reasoning behind each tool call differ.

---

## 6. Quick Sanity Checklist Before a Demo/Viva
- [ ] `python -m pytest tests/ -v` → 24 passed
- [ ] `npm run build` → 0 errors
- [ ] `/docs` loads and every `/maintenance/*` route listed in `README.md` responds
- [ ] `/maintenance` dashboard shows at least one Work Order with the `energy_agent`
      handoff badge (trigger it via `GET /maintenance/investigate` a couple of times if
      the seeded data doesn't already have one)
