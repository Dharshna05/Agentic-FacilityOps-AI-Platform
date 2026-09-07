from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import pandas as pd

from app.core.database import get_db
from app.core.security import require_role
from app.models.auth_models import User
from app.core.intelligence_engine import investigate_occupancy
from app.services import occupancy_service, occupancy_cnn_service
from app.agents.occupancy_agent import OccupancyAgent
from app.utils.occupancy_analytics import get_model_confidence, get_cnn_model_confidence, generate_ai_insights, best_available_zone
from app.utils.csv_upload import read_any, resolve_columns, save_upload_tmp
from app.models.occupancy_models import ZoneReading, Zone

router = APIRouter(prefix="/occupancy", tags=["occupancy"])

DEFAULT_BUILDING = "BLD-HQ-01"


@router.post("/ingest")
def ingest(db: Session = Depends(get_db)):
    """Milestone 3: integrate occupancy monitoring data. See
    data/build_occupancy_dataset.py for the real UCI Occupancy Detection
    source and the disclosed synthetic multi-zone projection."""
    try:
        result = occupancy_service.ingest_zones(db)
    except FileNotFoundError as e:
        raise HTTPException(503, str(e))
    return {"status": "ok", "building_id": DEFAULT_BUILDING, **result}


@router.get("/building")
def building(building_id: str = Query(DEFAULT_BUILDING), db: Session = Depends(get_db)):
    """Single call that powers the occupancy dashboard: building summary,
    all scored zones, heatmap data, and top alerts."""
    agent = OccupancyAgent(db, building_id)
    result = agent.run()
    analysis = result["analysis"]
    return {
        "building_id": building_id,
        "building": analysis["building"],
        "zones": analysis["zones"],
        "heatmap": analysis["heatmap"],
        "top_alerts": result["recommendations"][:8],
        "ai_insights": generate_ai_insights(analysis["zones"], analysis["building"]),
        "best_available_zone": best_available_zone(analysis["zones"]),
        "model_confidence": get_model_confidence(),
        "cnn_model_confidence": get_cnn_model_confidence(),
    }


@router.get("/cnn/summary")
def cnn_summary():
    """Lightweight, DB-free endpoint powering the standalone CNN Lab page —
    just the two models' metrics (no zone/agent queries needed), so the
    page loads instantly for a demo without pulling the full building
    payload."""
    return {
        "model_confidence": get_model_confidence(),
        "cnn_model_confidence": get_cnn_model_confidence(),
    }


@router.get("/zones")
def zones(building_id: str = Query(DEFAULT_BUILDING), db: Session = Depends(get_db)):
    agent = OccupancyAgent(db, building_id)
    analysis = agent.analyze()
    return {"building_id": building_id, "zones": analysis["zones"]}


@router.get("/zones/{zone_id}")
def zone_detail(zone_id: str, db: Session = Depends(get_db)):
    zone = occupancy_service.get_zone(db, zone_id)
    if not zone:
        raise HTTPException(404, f"Zone {zone_id} not found")
    readings = occupancy_service.get_readings_df(db, zone_id)
    if readings.empty:
        raise HTTPException(404, f"No readings for zone {zone_id}")
    from app.utils.occupancy_analytics import zone_status
    meta = {"zone_id": zone.zone_id, "name": zone.name, "zone_type": zone.zone_type, "capacity": zone.capacity}
    return zone_status(meta, readings)


@router.get("/zones/{zone_id}/history")
def zone_history(zone_id: str, limit: int = Query(200, le=1000), db: Session = Depends(get_db)):
    """Raw headcount history for a zone (for the utilization trend chart)."""
    readings = occupancy_service.get_readings_df(db, zone_id, limit=limit)
    if readings.empty:
        raise HTTPException(404, f"No readings for zone {zone_id}")
    return {"zone_id": zone_id, "readings": readings.to_dict(orient="records")}


@router.get("/alerts")
def alerts(building_id: str = Query(DEFAULT_BUILDING), db: Session = Depends(get_db)):
    agent = OccupancyAgent(db, building_id)
    return {"building_id": building_id, "alerts": agent.recommend()}


@router.get("/investigate")
def investigate(building_id: str = Query(DEFAULT_BUILDING)):
    """Genuinely agentic endpoint: the model decides which zones to
    inspect and whether a restricted zone's occupancy warrants a real
    handoff to the Security Agent."""
    return investigate_occupancy(building_id)


@router.get("/cnn/live-inference")
def cnn_live_inference():
    """Runs the ACTUAL trained CNN on a REAL held-out sensor window at
    request time — genuine live inference, not a precomputed report. Picks
    a random real example each call, so repeated calls show the model
    working on different real data, right vs wrong included."""
    result = occupancy_cnn_service.run_live_inference()
    if not result.get("available"):
        detail = result.get("message") or "CNN model or live-sample data not found — run train_occupancy_cnn.py first"
        raise HTTPException(503, detail)
    return result


# --- Manual dataset management (add / view / remove individual readings) ---

# --- Manual dataset management (add / view / remove individual readings) ---

OCCUPANCY_ALIASES = {
    "zone_id": ["zone_id", "zone", "room_id", "space_id"],
    "timestamp": ["timestamp", "date", "datetime", "time"],
    "headcount": ["headcount", "occupancy", "occupancy_count", "people_count", "count"],
    "utilization_pct": ["utilization_pct", "utilization", "utilization_percent"],
}


@router.post("/ingest/upload")
async def ingest_upload(
    file: UploadFile = File(...),
    replace: bool = Query(True, description="Clear existing readings before loading this file"),
    db: Session = Depends(get_db),
):
    """Upload your own headcount-readings CSV/Excel for the existing zone
    roster. Column names auto-detected (zone_id, headcount/occupancy,
    timestamp). utilization_pct is computed from each zone's capacity if
    not supplied. Every KPI, the zone heatmap, and both occupancy models
    recompute from whatever lands in the table."""
    tmp_path = save_upload_tmp(file)
    try:
        df = read_any(tmp_path)
        resolved = resolve_columns(df, OCCUPANCY_ALIASES, required={"zone_id", "headcount"})

        known_zones = {z.zone_id: z for z in db.query(Zone).all()}
        unknown = set(df[resolved["zone_id"]].astype(str).unique()) - set(known_zones)
        if unknown:
            raise HTTPException(
                400,
                f"Unknown zone_id value(s) {sorted(unknown)[:5]} — this building's zones are: {sorted(known_zones)[:10]}. "
                f"Upload readings for existing zones, or re-run /occupancy/ingest first to load a fresh zone roster.",
            )

        out = pd.DataFrame()
        out["zone_id"] = df[resolved["zone_id"]].astype(str)
        out["timestamp"] = pd.to_datetime(df[resolved["timestamp"]]) if "timestamp" in resolved else pd.Timestamp.utcnow()
        out["headcount"] = pd.to_numeric(df[resolved["headcount"]], errors="coerce")
        out["utilization_pct"] = pd.to_numeric(df[resolved["utilization_pct"]], errors="coerce") if "utilization_pct" in resolved else None
        out = out.dropna(subset=["zone_id", "headcount"])

        missing_util = out["utilization_pct"].isna()
        if missing_util.any():
            caps = out.loc[missing_util, "zone_id"].map(lambda z: known_zones[z].capacity or 0)
            out.loc[missing_util, "utilization_pct"] = (100 * out.loc[missing_util, "headcount"] / caps.replace(0, pd.NA)).round(1).fillna(0.0)

        if replace:
            for zone_id in out["zone_id"].unique():
                db.query(ZoneReading).filter(ZoneReading.zone_id == zone_id).delete()

        rows = [ZoneReading(zone_id=r.zone_id, timestamp=r.timestamp, headcount=int(r.headcount), utilization_pct=float(r.utilization_pct))
                for r in out.itertuples(index=False)]
        db.bulk_save_objects(rows)
        db.commit()
        return {"status": "ok", "rows_ingested": len(rows), "zones_affected": sorted(out["zone_id"].unique().tolist())}
    except ValueError as e:
        raise HTTPException(400, str(e))
    finally:
        tmp_path.unlink(missing_ok=True)


class ZoneReadingIn(BaseModel):
    zone_id: str
    timestamp: datetime | None = None
    headcount: int
    utilization_pct: float | None = None


@router.get("/records/recent")
def recent_records(zone_id: str | None = Query(None), limit: int = Query(20, le=200), db: Session = Depends(get_db)):
    """Most recent N raw headcount readings, for the dataset-management table."""
    q = db.query(ZoneReading)
    if zone_id:
        q = q.filter(ZoneReading.zone_id == zone_id)
    rows = q.order_by(ZoneReading.timestamp.desc()).limit(limit).all()
    return {"records": [{
        "id": r.id, "zone_id": r.zone_id, "timestamp": r.timestamp,
        "headcount": r.headcount, "utilization_pct": r.utilization_pct,
    } for r in rows]}


@router.post("/records")
def add_record(payload: ZoneReadingIn, db: Session = Depends(get_db), current_user: User = Depends(require_role("admin", "technician"))):
    """Add one manual headcount reading for a zone."""
    utilization = payload.utilization_pct
    if utilization is None:
        zone = db.query(Zone).filter(Zone.zone_id == payload.zone_id).first()
        utilization = round(100 * payload.headcount / zone.capacity, 1) if zone and zone.capacity else 0.0
    row = ZoneReading(
        zone_id=payload.zone_id,
        timestamp=payload.timestamp or datetime.utcnow(),
        headcount=payload.headcount,
        utilization_pct=utilization,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"status": "ok", "id": row.id}


@router.delete("/records/{record_id}")
def delete_record(record_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role("admin", "technician"))):
    """Remove one headcount reading by id."""
    row = db.query(ZoneReading).filter(ZoneReading.id == record_id).first()
    if not row:
        raise HTTPException(404, "Reading not found")
    db.delete(row)
    db.commit()
    return {"status": "ok", "deleted_id": record_id}


@router.delete("/records")
def clear_all_records(zone_id: str | None = Query(None), db: Session = Depends(get_db), current_user: User = Depends(require_role("admin", "technician"))):
    """Wipe every headcount reading — or just one zone's, if zone_id is
    given — with no replacement loaded."""
    q = db.query(ZoneReading)
    if zone_id:
        q = q.filter(ZoneReading.zone_id == zone_id)
    deleted = q.delete()
    db.commit()
    return {"status": "ok", "deleted_count": deleted}
