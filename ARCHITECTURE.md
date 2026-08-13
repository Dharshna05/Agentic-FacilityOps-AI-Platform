# Architecture — How Future Milestones Plug In

This document exists so Milestones 2–4 (Maintenance, Occupancy, Security/Cost agents,
and cross-agent orchestration) can be added **without rewriting Milestone 1**. Every
piece of the Energy module was built as a repeatable template, not a one-off.

**Status: Milestone 1 (Energy) ✅ and Milestone 2 (Maintenance) ✅ both complete,
following this exact pattern — see README.md for what each one does. Milestones
3–4 (Occupancy, Security/Cost, cross-agent orchestration) are still future work.**

## The pattern each new agent follows

Every domain agent — Energy (done), Maintenance (done), Occupancy, Security, Cost
(future) — follows the same four-part structure, established in
`backend/app/agents/energy_agent.py` and reused as-is in
`backend/app/agents/maintenance_agent.py`:

```
class <Domain>Agent:
    def __init__(self, db, building_id):   # pulls the data it needs
    def analyze(self) -> dict:             # runs domain-specific analytics
    def recommend(self, analysis) -> list: # turns analysis into ranked actions
    def run(self) -> dict:                 # single entrypoint: analyze + recommend
```

To add a new agent, copy this shape into a new file
(`backend/app/agents/maintenance_agent.py`, etc.) — nothing in `energy_agent.py` needs
to change.

## Where each future milestone's pieces go (folders already exist for this)

| Layer | Energy (done) | Maintenance (future) | Occupancy (future) |
|---|---|---|---|
| DB model | `app/models/energy_models.py` | `app/models/maintenance_models.py` | `app/models/occupancy_models.py` |
| Analytics | `app/utils/energy_analytics.py` | `app/utils/maintenance_analytics.py` | `app/utils/occupancy_analytics.py` |
| Agent | `app/agents/energy_agent.py` | `app/agents/maintenance_agent.py` | `app/agents/occupancy_agent.py` |
| ML model | `ml_models/energy/` | `ml_models/maintenance/` | `ml_models/occupancy/` |
| API routes | `app/api/routes.py` (`/energy/*`) | new file, mounted at `/maintenance/*` | new file, mounted at `/occupancy/*` |
| Frontend page | `frontend/src/pages/energy/` | `frontend/src/pages/maintenance/` | `frontend/src/pages/occupancy/` |

Each new agent's router gets registered in `backend/app/main.py` the same way the
energy router is (`app.include_router(...)`) — additive, not a rewrite of existing routes.

## The agentic tool + provider layer already generalizes

`backend/app/services/ai_providers/` (MockProvider, GroqProvider, GeminiProvider) is not
Energy-specific — any future agent's tools can be passed through the same
`run_agentic_task()` interface. `backend/app/core/agent_tools.py` currently holds only
Energy's tools; a Maintenance milestone would add its own tool functions to a new
`maintenance_tools.py` (or extend the same file) and pass them into
`intelligence_engine.investigate_energy()`'s equivalent for that domain — the provider
code itself needs zero changes.

The `flag_for_maintenance_review()` tool already exists in `agent_tools.py` as a stub —
when the Maintenance Agent is built, that tool's implementation becomes real (creates an
actual work order) instead of just recording a flag. This is the intended cross-agent
handoff seam.

## Cross-agent orchestration (Milestone 4+)

When multiple agents exist, a future `app/core/orchestrator.py` can coordinate them —
e.g. take Energy's anomaly + Occupancy's headcount data together to reason about
root cause. This wasn't built yet (only one agent exists), but the tool-calling pattern
already used for the single-agent investigation (`investigate_energy()`) extends
directly: an orchestrator is just a provider call with a bigger tool list drawn from
multiple agents' tool files.

## What NOT to change when adding new milestones

- `app/core/database.py`, `app/core/config.py` — shared infrastructure, extend via new
  env vars / new imports in `init_db()`, don't restructure
- `app/services/ai_providers/*` — generic, works for any agent's tools already
- Existing Energy endpoints/tests — additive only; a regression here breaks Milestone 1
