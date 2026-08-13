# Documentation Task Brief (Teammate 2)

Everything below is a raw fact/number you can use. Write it up in your own words —
don't copy-paste this file directly into the README or report, that'll read as
obviously AI-written to the professor. Explain it like you understand it.

## Your two deliverables
1. Fill in the "Milestone 2" section of `README.md` (marked with a TODO checklist there)
2. Write a short process report for the professor: what was built, why NASA C-MAPSS was
   chosen over a Kaggle dataset, roughly how long each part took, what was difficult

---

## Dataset facts

- **Source**: NASA C-MAPSS Turbofan Engine Degradation Simulation, FD001 subset
  (originally published by Saxena & Goebel, 2008, as part of NASA's Prognostics Data
  Repository)
- **Obtained via**: GitHub mirror `github.com/edwardzjl/CMAPSSData` (raw files are
  committed at `backend/data/raw_maintenance/` in this repo — you can open them yourself)
- **Why not Kaggle**: most good predictive-maintenance datasets on Kaggle require a
  Kaggle account/API key to download programmatically; this GitHub mirror is directly
  fetchable and is the same underlying NASA data
- **Size**: 100 engines used for training (each engine has its full run-to-failure
  sensor history — anywhere from 128 to 362 operating cycles), plus NASA's own official
  held-out test set of 100 more engines with a separate "answer key" file (RUL_FD001.txt)
  giving the true remaining life
- **Real vs. relabeled**: the sensor VALUES and how they degrade over time are 100% real
  physical measurements from real engines run to real failure. The NAMES were changed —
  e.g. what NASA calls "sensor 11" (HPC outlet static pressure) is relabeled
  "vibration_index" and assigned to a fictional facility asset like "Chiller-042" instead
  of "Engine unit 42". This is explained honestly in the code
  (`backend/data/build_maintenance_dataset.py`) and in the README — it's not hidden.
- **Why this is defensible**: there's no free, high-quality, sensor-level "run to
  failure" dataset for actual facility HVAC/pump equipment publicly available. What
  matters for the ML task is that the sensors show REAL degradation patterns as a
  machine approaches failure — that's what NASA's data genuinely provides.

## ML model facts

- **What it predicts**: Remaining Useful Life (RUL) — how many more operating days
  (cycles) before an asset needs maintenance
- **Algorithms compared**: Linear Regression, Random Forest, Gradient Boosting
- **Winner**: Gradient Boosting
- **Held-out test accuracy**: MAE 14.81 cycles (vs. a naive baseline of 34.83 cycles —
  i.e. "always guess the average") — a 57.5% improvement over that naive baseline
- **Held-out test set**: NASA's own official 100 test engines — genuinely never seen
  during training
- **RUL clipping at 125**: standard practice in this field — far from failure, sensor
  readings don't distinguish "300 cycles left" from "280 cycles left" cleanly, so the
  model is asked the more useful/answerable question of "how close to failure, up to
  ~125 cycles out"
- **Exact numbers**: see `backend/ml_models/maintenance/model_metrics.json` after
  running `python ml_models/maintenance/train_health_model.py` (already run once —
  the file exists in the repo, just open it)

## Architecture facts

- **Maintenance Agent** follows the same 4-step pattern as the Energy Agent from
  Milestone 1: `analyze()` (run the ML model + rules on the current data),
  `recommend()` (turn that into ranked alerts), `run()` (single entrypoint)
- **Agentic tools** (functions the LLM can call on its own): checking fleet-wide health,
  checking one asset's health, listing at-risk assets, opening a work order
- **Cross-agent handoff**: previously (Milestone 1), the Energy Agent had a tool called
  `flag_for_maintenance_review` that just wrote a log line — a placeholder for a future
  milestone. Now it actually calls the same function the Maintenance Agent itself uses to
  create work orders, so a real record shows up in the Maintenance module's Work Orders
  list, tagged as coming from the Energy Agent. This is the part that shows the two
  agents are genuinely cooperating, not just two separate features in one codebase.
- **New API endpoints**: `POST /api/maintenance/ingest`, `GET /api/maintenance/fleet`,
  `GET /api/maintenance/assets`, `GET /api/maintenance/assets/{id}`,
  `GET /api/maintenance/assets/{id}/history`, `GET /api/maintenance/alerts`,
  `GET /api/maintenance/work-orders`, `GET /api/maintenance/investigate`,
  `GET /api/maintenance/model/scatter`
- **Frontend additions**: a sidebar (Energy ⇄ Maintenance navigation), a Maintenance
  dashboard page, a "Fleet Health Radar" (custom SVG chart, similar idea to a radar
  chart, showing every asset's health at a glance), and reliability scatter charts
  (actual-vs-predicted) on both dashboards showing how trustworthy each ML model is

## Testing facts

- Run `cd backend && python -m pytest tests/ -v` yourself and copy the actual output
  into your report — don't just take this file's word for it
- Expect: 24 tests total (13 from Milestone 1, 11 new for Milestone 2), all passing
- The most important new test (`test_cross_agent_handoff_creates_real_work_order`)
  verifies the Energy → Maintenance handoff creates an actual database row, not just a
  log message — that's the test worth explaining in detail if the professor asks
  "how do you know the agents are really talking to each other?"

## Suggested process report structure

1. What Milestone 2 adds (one paragraph)
2. Data: what NASA C-MAPSS is, why it was chosen, honest caveat about relabeling
3. Time taken (fill in realistically for your team)
4. What was difficult (pick 2-3 genuinely hard things — e.g. "getting a real, not
   simulated, cross-agent handoff working" or "evaluating a model honestly instead of
   just accepting a suspiciously high accuracy number" are good, true things to discuss)
5. What each team member worked on (see TEAM_TASKS.md)
