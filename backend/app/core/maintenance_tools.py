"""
Tools available to the Maintenance Agent's agentic investigation loop —
same pattern as app/core/agent_tools.py for Energy (see that file's
docstring for the rationale). Each function is self-contained (opens/closes
its own DB session) so it's directly callable by the LLM SDK's
function-calling machinery.
"""
from app.core.database import SessionLocal
from app.services import maintenance_service
from app.utils.maintenance_analytics import score_asset, fleet_summary, risk_ranking


def get_fleet_summary(building_id: str = "BLD-HQ-01") -> dict:
    """Get fleet-wide maintenance health: how many assets are monitored,
    average health score (0-100), and how many fall into each status
    bucket (Excellent/Good/Warning/Critical).

    Args:
        building_id: The building identifier, e.g. "BLD-HQ-01".
    """
    db = SessionLocal()
    try:
        assets = maintenance_service.list_assets(db, building_id)
        scored = []
        for a in assets:
            readings = maintenance_service.get_readings_df(db, a.asset_id)
            if readings.empty:
                continue
            meta = {"asset_id": a.asset_id, "name": a.name, "asset_type": a.asset_type, "location": a.location}
            scored.append(score_asset(meta, readings))
        return fleet_summary(scored)
    finally:
        db.close()


def get_asset_health(asset_id: str) -> dict:
    """Get the detailed ML-predicted health for one specific asset:
    predicted remaining useful life (in operating days), health score
    (0-100), status bucket, predicted maintenance date, and the model's
    own confidence for this prediction.

    Args:
        asset_id: The asset identifier, e.g. "AST-001".
    """
    db = SessionLocal()
    try:
        asset = maintenance_service.get_asset(db, asset_id)
        if not asset:
            return {"error": f"asset {asset_id} not found"}
        readings = maintenance_service.get_readings_df(db, asset_id)
        meta = {"asset_id": asset.asset_id, "name": asset.name, "asset_type": asset.asset_type, "location": asset.location}
        return score_asset(meta, readings)
    finally:
        db.close()


def get_at_risk_assets(building_id: str = "BLD-HQ-01", max_health_score: float = 50.0) -> list:
    """Get the assets currently most at risk (lowest predicted health
    scores), sorted worst-first. Use this to decide which specific assets
    need a closer look or a work order.

    Args:
        building_id: The building identifier, e.g. "BLD-HQ-01".
        max_health_score: Only return assets at or below this health score (0-100).
    """
    db = SessionLocal()
    try:
        assets = maintenance_service.list_assets(db, building_id)
        scored = []
        for a in assets:
            readings = maintenance_service.get_readings_df(db, a.asset_id)
            if readings.empty:
                continue
            meta = {"asset_id": a.asset_id, "name": a.name, "asset_type": a.asset_type, "location": a.location}
            scored.append(score_asset(meta, readings))
        at_risk = [a for a in scored if a["health_score"] <= max_health_score]
        return risk_ranking(at_risk, limit=10)
    finally:
        db.close()


def create_work_order(asset_id: str, reason: str, severity: str = "medium") -> dict:
    """Open a real maintenance work order for a specific asset. Use this
    when you've found clear evidence (Critical status, or Warning + a
    worsening trend) that maintenance should actually be scheduled — not
    for every asset you merely check.

    Args:
        asset_id: The asset identifier, e.g. "AST-001".
        reason: A concise explanation of what was found and why it warrants a work order.
        severity: One of "low", "medium", "high".
    """
    db = SessionLocal()
    try:
        return maintenance_service.open_work_order(
            db, asset_id=asset_id, reason=reason, severity=severity, source="maintenance_agent"
        )
    finally:
        db.close()


ALL_TOOLS = [
    get_fleet_summary,
    get_asset_health,
    get_at_risk_assets,
    create_work_order,
]
