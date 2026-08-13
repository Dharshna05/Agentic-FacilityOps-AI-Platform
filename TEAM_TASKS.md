# Milestone 2 — Team Task Division

## Aryan — Backend + Agentic AI core (done)
- Maintenance Agent (`backend/app/agents/maintenance_agent.py`)
- ML health/RUL model + training + evaluation (`backend/ml_models/maintenance/`)
- Agentic tool-calling layer + real cross-agent handoff (`backend/app/core/maintenance_tools.py`,
  `backend/app/core/agent_tools.py`)
- All API routes (`backend/app/api/maintenance_routes.py`)
- Dataset pipeline (`backend/data/build_maintenance_dataset.py`)
- ML reliability charts wiring (backend scatter endpoints + frontend chart component)

## Teammate 1 — Frontend
Files to complete (each has a TODO comment with the full spec inside):
- [ ] `frontend/src/components/maintenance/FleetHealthRadar.jsx` — signature visual
- [ ] `frontend/src/components/maintenance/AssetTable.jsx` — sortable asset list
- [ ] `frontend/src/components/maintenance/MaintenanceAlertsList.jsx`
- [ ] `frontend/src/components/maintenance/WorkOrdersPanel.jsx`
- [ ] `frontend/src/components/maintenance/FleetKpiRow.jsx`

The page that wires these together (`frontend/src/pages/maintenance/MaintenanceDashboardPage.jsx`)
already calls all of them correctly with the right props — you don't need to touch it,
just implement each component to actually render its data instead of the placeholder text.

To run and see your work live:
```
cd backend && python -m pip install -r requirements.txt && python -m uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
```
Then open http://localhost:5173/maintenance — the placeholder TODO boxes are exactly
where your components render.

## Teammate 2 — Documentation + verification
See `DOCUMENTATION_TASK.md` for the full brief with every fact/number you need.
- [ ] Fill in the "Milestone 2" section of `README.md` (currently a TODO checklist)
- [ ] Run `pytest tests/ -v` in `backend/`, confirm 24/24 pass, log the output
- [ ] Manually test each new endpoint via `/docs` (Swagger UI) once the backend is running
- [ ] Write the process report for the professor (structure suggested in DOCUMENTATION_TASK.md)
- [ ] Take screenshots of the working dashboard + agent trace for the submission
