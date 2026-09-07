from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path
import pandas as pd

from app.core.database import get_db
from app.core.security import require_role
from app.models.auth_models import User
from app.core.intelligence_engine import investigate_maintenance
from app.services import maintenance_service
from app.agents.maintenance_agent import MaintenanceAgent
from app.models.maintenance_models import AssetReading, Asset
from app.utils.csv_upload import read_any, resolve_columns, save_upload_tmp

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
    from app.services import health_service
    agent = MaintenanceAgent(db, building_id)
    result = agent.run()
    analysis = result["analysis"]
    return {
        "building_id": building_id,
        "fleet": analysis["fleet"],
        "assets": analysis["assets"],
        "risk_ranking": analysis["risk_ranking"],
        "top_alerts": result["recommendations"][:8],
        "model_confidence": health_service.get_confidence(),
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


# --- Manual dataset management (add / view / remove individual readings) ---

MAINTENANCE_ALIASES = {
    "asset_id": ["asset_id", "asset", "equipment_id", "unit_id", "machine_id"],
    "cycle": ["cycle", "cycle_number", "time_cycles", "operating_cycle"],
    "timestamp": ["timestamp", "date", "datetime", "time"],
    "temp_stage1_c": ["temp_stage1_c", "temperature_1", "temp1", "t1"],
    "temp_stage2_c": ["temp_stage2_c", "temperature_2", "temp2", "t2"],
    "temp_stage3_c": ["temp_stage3_c", "temperature_3", "temp3", "t3"],
    "pressure_kpa": ["pressure_kpa", "pressure", "pressure_psi"],
    "vibration_index": ["vibration_index", "vibration", "vib"],
    "flow_rate": ["flow_rate", "flow", "flowrate"],
    "efficiency_ratio": ["efficiency_ratio", "efficiency"],
    "bleed_load": ["bleed_load", "bleed"],
}


@router.post("/ingest/upload")
async def ingest_upload(
    file: UploadFile = File(...),
    replace: bool = Query(True, description="Clear existing readings before loading this file"),
    db: Session = Depends(get_db),
):
    """Upload your own sensor-readings CSV/Excel file for the existing
    asset fleet. Column names are auto-detected (asset_id, vibration,
    pressure, temperature stages, etc. under common aliases). Rows for
    an unrecognized asset_id are rejected with a clear list of the
    fleet's actual asset IDs, rather than silently dropped — every
    downstream KPI, the Fleet Health Radar, and the RUL model all
    recompute from whatever lands in the table, nothing is hardcoded."""
    tmp_path = save_upload_tmp(file)
    try:
        df = read_any(tmp_path)
        resolved = resolve_columns(df, MAINTENANCE_ALIASES, required={"asset_id", "vibration_index"})

        known_assets = {a.asset_id for a in db.query(Asset.asset_id).all()}
        unknown = set(df[resolved["asset_id"]].astype(str).unique()) - known_assets
        if unknown:
            raise HTTPException(
                400,
                f"Unknown asset_id value(s) {sorted(unknown)[:5]} — this fleet has {len(known_assets)} assets, e.g. {sorted(known_assets)[:10]}. "
                f"Upload readings for existing assets, or re-run /maintenance/ingest first to load a fresh fleet.",
            )

        out = pd.DataFrame()
        out["asset_id"] = df[resolved["asset_id"]].astype(str)
        out["timestamp"] = pd.to_datetime(df[resolved["timestamp"]]) if "timestamp" in resolved else pd.Timestamp.utcnow()
        out["vibration_index"] = pd.to_numeric(df[resolved["vibration_index"]], errors="coerce")
        for opt in ["cycle", "temp_stage1_c", "temp_stage2_c", "temp_stage3_c", "pressure_kpa", "flow_rate", "efficiency_ratio", "bleed_load"]:
            out[opt] = pd.to_numeric(df[resolved[opt]], errors="coerce") if opt in resolved else None
        out = out.dropna(subset=["asset_id", "vibration_index"])

        if replace:
            for asset_id in out["asset_id"].unique():
                db.query(AssetReading).filter(AssetReading.asset_id == asset_id).delete()

        next_cycle = {}
        rows = []
        for r in out.itertuples(index=False):
            cycle = r.cycle
            if pd.isna(cycle):
                cycle = next_cycle.get(r.asset_id, 1)
            next_cycle[r.asset_id] = int(cycle) + 1
            rows.append(AssetReading(
                asset_id=r.asset_id, cycle=int(cycle), timestamp=r.timestamp,
                temp_stage1_c=r.temp_stage1_c, temp_stage2_c=r.temp_stage2_c, temp_stage3_c=r.temp_stage3_c,
                pressure_kpa=r.pressure_kpa, vibration_index=r.vibration_index,
                flow_rate=r.flow_rate, efficiency_ratio=r.efficiency_ratio, bleed_load=r.bleed_load,
            ))
        db.bulk_save_objects(rows)
        db.commit()
        return {"status": "ok", "rows_ingested": len(rows), "assets_affected": sorted(out["asset_id"].unique().tolist())}
    except ValueError as e:
        raise HTTPException(400, str(e))
    finally:
        tmp_path.unlink(missing_ok=True)


class AssetReadingIn(BaseModel):
    asset_id: str
    cycle: int | None = None
    timestamp: datetime | None = None
    temp_stage1_c: float | None = None
    temp_stage2_c: float | None = None
    temp_stage3_c: float | None = None
    pressure_kpa: float | None = None
    vibration_index: float | None = None
    flow_rate: float | None = None
    efficiency_ratio: float | None = None
    bleed_load: float | None = None


@router.get("/records/recent")
def recent_records(asset_id: str | None = Query(None), limit: int = Query(20, le=200), db: Session = Depends(get_db)):
    """Most recent N raw sensor readings, for the dataset-management table."""
    q = db.query(AssetReading)
    if asset_id:
        q = q.filter(AssetReading.asset_id == asset_id)
    rows = q.order_by(AssetReading.timestamp.desc()).limit(limit).all()
    return {"records": [{
        "id": r.id, "asset_id": r.asset_id, "cycle": r.cycle, "timestamp": r.timestamp,
        "temp_stage1_c": r.temp_stage1_c, "temp_stage2_c": r.temp_stage2_c, "temp_stage3_c": r.temp_stage3_c,
        "pressure_kpa": r.pressure_kpa, "vibration_index": r.vibration_index,
        "flow_rate": r.flow_rate, "efficiency_ratio": r.efficiency_ratio, "bleed_load": r.bleed_load,
    } for r in rows]}


@router.post("/records")
def add_record(payload: AssetReadingIn, db: Session = Depends(get_db), current_user: User = Depends(require_role("admin", "technician"))):
    """Add one manual sensor reading for an asset."""
    last = (db.query(AssetReading).filter(AssetReading.asset_id == payload.asset_id)
            .order_by(AssetReading.cycle.desc()).first())
    row = AssetReading(
        asset_id=payload.asset_id,
        cycle=payload.cycle if payload.cycle is not None else ((last.cycle + 1) if last else 1),
        timestamp=payload.timestamp or datetime.utcnow(),
        temp_stage1_c=payload.temp_stage1_c, temp_stage2_c=payload.temp_stage2_c,
        temp_stage3_c=payload.temp_stage3_c, pressure_kpa=payload.pressure_kpa,
        vibration_index=payload.vibration_index, flow_rate=payload.flow_rate,
        efficiency_ratio=payload.efficiency_ratio, bleed_load=payload.bleed_load,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"status": "ok", "id": row.id}


@router.delete("/records/{record_id}")
def delete_record(record_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role("admin", "technician"))):
    """Remove one sensor reading by id."""
    row = db.query(AssetReading).filter(AssetReading.id == record_id).first()
    if not row:
        raise HTTPException(404, "Reading not found")
    db.delete(row)
    db.commit()
    return {"status": "ok", "deleted_id": record_id}


@router.delete("/records")
def clear_all_records(asset_id: str | None = Query(None), db: Session = Depends(get_db), current_user: User = Depends(require_role("admin", "technician"))):
    """Wipe every sensor reading — or just one asset's, if asset_id is
    given — with no replacement loaded. Distinct from /ingest (loads the
    bundled fleet dataset) and /ingest/upload (loads a new file)."""
    q = db.query(AssetReading)
    if asset_id:
        q = q.filter(AssetReading.asset_id == asset_id)
    deleted = q.delete()
    db.commit()
    return {"status": "ok", "deleted_count": deleted}
