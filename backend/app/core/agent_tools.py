"""
Tools available to the Energy Agent's agentic investigation loop.

This is what actually makes the system "agentic" rather than a single
LLM summarization call: each function below is a real capability
(query the DB, run analytics, run the ML model, or signal another agent).
The LLM is given these as callable tools and DECIDES, at each step, which
ones to call and in what order — it is not a fixed pipeline we wrote.

Each function is self-contained (opens/closes its own DB session) because
it needs to be callable directly by the LLM SDK's function-calling
machinery, outside the normal FastAPI request/response cycle.

Docstrings are deliberately written in plain English with clear parameter
descriptions because Gemini's automatic function calling reads them to
decide when a tool is relevant — vague docstrings produce worse tool choices.
"""
from app.core.database import SessionLocal
from app.services import data_service, forecast_service, maintenance_service
from app.utils import energy_analytics


def get_consumption_summary(building_id: str = "BLD-HQ-01") -> dict:
    """Get total, average, peak, and minimum energy consumption (in kWh)
    for a building over the currently loaded monitoring period.

    Args:
        building_id: The building identifier, e.g. "BLD-HQ-01".
    """
    db = SessionLocal()
    try:
        df = data_service.get_readings_df(db, building_id)
        return energy_analytics.consumption_summary(df)
    finally:
        db.close()


def get_submeter_breakdown(building_id: str = "BLD-HQ-01") -> dict:
    """Get the percentage breakdown of energy consumption across HVAC,
    Lighting, Plug Load, and Other submeters for a building.

    Args:
        building_id: The building identifier, e.g. "BLD-HQ-01".
    """
    db = SessionLocal()
    try:
        df = data_service.get_readings_df(db, building_id)
        return energy_analytics.submeter_breakdown(df)
    finally:
        db.close()


def get_anomalies(building_id: str = "BLD-HQ-01") -> list:
    """Get a list of detected consumption anomalies for a building — hours
    where usage deviated sharply from the expected pattern for that time of
    day. Each anomaly includes a timestamp, actual vs expected kWh, and
    severity (medium/high). Use this to check for equipment problems.

    Args:
        building_id: The building identifier, e.g. "BLD-HQ-01".
    """
    db = SessionLocal()
    try:
        df = data_service.get_readings_df(db, building_id)
        return energy_analytics.detect_anomalies(df)[:10]  # cap for token budget
    finally:
        db.close()


def get_temperature_correlation(building_id: str = "BLD-HQ-01") -> dict:
    """Get how strongly energy consumption correlates with outdoor
    temperature for a building. Low correlation despite high HVAC share can
    indicate a stuck setpoint or damper fault. Use this when investigating
    HVAC-related efficiency questions.

    Args:
        building_id: The building identifier, e.g. "BLD-HQ-01".
    """
    db = SessionLocal()
    try:
        df = data_service.get_readings_df(db, building_id)
        return energy_analytics.temperature_correlation(df)
    finally:
        db.close()


def get_occupancy_correlation(building_id: str = "BLD-HQ-01") -> dict:
    """Get how strongly energy consumption correlates with building
    occupancy (headcount). High consumption during zero-occupancy periods
    indicates wasted load not tied to actual building use. Use this when
    investigating scheduling or waste-reduction questions.

    Args:
        building_id: The building identifier, e.g. "BLD-HQ-01".
    """
    db = SessionLocal()
    try:
        df = data_service.get_readings_df(db, building_id)
        return energy_analytics.occupancy_correlation(df)
    finally:
        db.close()


def get_ml_forecast(building_id: str = "BLD-HQ-01", horizon: str = "1h") -> dict:
    """Get the machine-learning-predicted energy consumption for a future
    point in time, from a trained regression model — a DIFFERENT model is
    used per horizon, each with its own accuracy. Use "1h" for near-term
    questions (high accuracy — ~65% better than a naive guess). Use "6h"
    for same-day planning (still fairly accurate). Use "24h" for next-day
    outlook, but treat it with caution — the trained model for 24h is only
    marginally better than a naive guess (this is reported honestly in the
    response's confidence field, don't overstate a 24h prediction's
    reliability).

    Args:
        building_id: The building identifier, e.g. "BLD-HQ-01".
        horizon: One of "1h", "6h", "24h" — how far ahead to predict.
    """
    db = SessionLocal()
    try:
        df = data_service.get_readings_df(db, building_id)
        return forecast_service.forecast(df, horizon=horizon)
    finally:
        db.close()


def flag_for_maintenance_review(reason: str, severity: str = "medium", building_id: str = "BLD-HQ-01") -> dict:
    """Flag a finding for the Maintenance Agent to review — use this when
    you find evidence suggesting equipment malfunction (e.g. repeated
    anomalies, a load pattern that doesn't respond to temperature the way
    working HVAC should) rather than a scheduling/behavioral issue. This
    creates a REAL maintenance work order (cross-agent handoff, not just a
    logged note) — the Maintenance Agent's own dashboard and work-order
    list will show it, tagged with source="energy_agent".

    Args:
        reason: A concise explanation of what was found and why it looks
            like a hardware/maintenance issue rather than a scheduling one.
        severity: One of "low", "medium", "high".
        building_id: The building identifier, e.g. "BLD-HQ-01".
    """
    db = SessionLocal()
    try:
        asset_id = maintenance_service.pick_hvac_asset_for_energy_flag(db, building_id)
        if not asset_id:
            return {
                "status": "not_flagged",
                "reason": reason,
                "severity": severity,
                "note": "No maintenance assets ingested for this building yet — "
                        "run POST /api/maintenance/ingest first.",
            }
        work_order = maintenance_service.open_work_order(
            db, asset_id=asset_id, reason=reason, severity=severity,
            source="energy_agent", building_id=building_id,
        )
        return {
            "status": "flagged",
            "work_order_id": work_order["id"],
            "asset_id": asset_id,
            "reason": reason,
            "severity": severity,
            "note": f"Real work order #{work_order['id']} opened for {asset_id} "
                    "via cross-agent handoff to the Maintenance Agent.",
        }
    finally:
        db.close()


ALL_TOOLS = [
    get_consumption_summary,
    get_submeter_breakdown,
    get_anomalies,
    get_temperature_correlation,
    get_occupancy_correlation,
    get_ml_forecast,
    flag_for_maintenance_review,
]
