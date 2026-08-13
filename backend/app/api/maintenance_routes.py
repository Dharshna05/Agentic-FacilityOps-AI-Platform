from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.intelligence_engine import investigate_maintenance
from app.services import maintenance_service
from app.agents.maintenance_agent import MaintenanceAgent

router = APIRouter(prefix="/maintenance", tags=["maintenance"])

DEFAULT_BUILDING = "BLD-HQ-01"


@router.post("/ingest")
def ingest(db: Session = Depends(get_db)):
    """Milestone 2: integrate asset monitoring data. Loads the configured
    fleet dataset into the database — see data/build_maintenance_dataset.py
    for the real NASA C-MAPSS source and honest domain-relabeling caveat."""
    try:
        result = maintenance_service.ingest_fleet(db)
    except FileNotFoundError as e:
        raise HTTPException(503, str(e))
    return {"status": "ok", "building_id": DEFAULT_BUILDING, **result}


@router.get("/fleet")
def fleet(building_id: str = Query(DEFAULT_BUILDING), db: Session = Depends(get_db)):
    """Single call that powers the maintenance dashboard: fleet summary,
    all scored assets, risk ranking, and top alerts."""
    agent = MaintenanceAgent(db, building_id)
    result = agent.run()
    analysis = result["analysis"]
    return {
        "building_id": building_id,
        "fleet": analysis["fleet"],
        "assets": analysis["assets"],
        "risk_ranking": analysis["risk_ranking"],
        "top_alerts": result["recommendations"][:8],
    }


@router.get("/assets")
def assets(building_id: str = Query(DEFAULT_BUILDING), db: Session = Depends(get_db)):
    agent = MaintenanceAgent(db, building_id)
    analysis = agent.analyze()
    return {"building_id": building_id, "assets": analysis["assets"]}


@router.get("/assets/{asset_id}")
def asset_detail(asset_id: str, db: Session = Depends(get_db)):
    asset = maintenance_service.get_asset(db, asset_id)
    if not asset:
        raise HTTPException(404, f"Asset {asset_id} not found")
    readings = maintenance_service.get_readings_df(db, asset_id)
    if readings.empty:
        raise HTTPException(404, f"No readings for asset {asset_id}")
    from app.utils.maintenance_analytics import score_asset
    meta = {"asset_id": asset.asset_id, "name": asset.name, "asset_type": asset.asset_type, "location": asset.location}
    scored = score_asset(meta, readings)
    return scored


@router.get("/assets/{asset_id}/history")
def asset_history(asset_id: str, limit: int = Query(200, le=500), db: Session = Depends(get_db)):
    """Raw sensor history for an asset (for the sensor-trend chart)."""
    readings = maintenance_service.get_readings_df(db, asset_id)
    if readings.empty:
        raise HTTPException(404, f"No readings for asset {asset_id}")
    tail = readings.tail(limit)
    return {"asset_id": asset_id, "readings": tail.to_dict(orient="records")}


@router.get("/alerts")
def alerts(building_id: str = Query(DEFAULT_BUILDING), db: Session = Depends(get_db)):
    agent = MaintenanceAgent(db, building_id)
    return {"building_id": building_id, "alerts": agent.recommend()}


@router.get("/model/scatter")
def model_scatter():
    """Actual-vs-predicted RUL on the 100 NASA held-out test engines for
    the winning health model — same reliability diagnostic as the Energy
    forecast scatter."""
    from app.services import health_service
    try:
        return health_service.get_prediction_scatter()
    except FileNotFoundError as e:
        raise HTTPException(503, str(e))


@router.get("/work-orders")
def work_orders(
    building_id: str = Query(DEFAULT_BUILDING),
    status: str | None = Query(None, description="Filter: 'open' or 'resolved'"),
    db: Session = Depends(get_db),
):
    """All work orders, including ones created via the Energy Agent's
    cross-agent handoff (source='energy_agent') — auditable proof the
    handoff is real, not just a logged note."""
    return {"building_id": building_id, "work_orders": maintenance_service.list_work_orders(db, building_id, status)}


@router.get("/investigate")
def investigate(building_id: str = Query(DEFAULT_BUILDING)):
    """Genuinely agentic endpoint, same pattern as /api/energy/investigate:
    the model decides which assets to inspect and whether to open a work
    order, and the full tool-call trace is returned."""
    return investigate_maintenance(building_id)
