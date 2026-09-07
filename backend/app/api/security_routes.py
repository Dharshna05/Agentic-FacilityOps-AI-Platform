from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import uuid
import pandas as pd

from app.core.database import get_db
from app.core.security import require_role
from app.models.auth_models import User
from app.core.intelligence_engine import investigate_security
from app.services import security_service
from app.agents.security_agent import SecurityAgent
from app.utils.security_analytics import get_model_confidence, get_comparison_model_confidence, get_supervised_reference_confidence, get_data_drift
from app.utils.csv_upload import read_any, resolve_columns, save_upload_tmp
from app.models.security_models import AccessEvent, AccessPoint

router = APIRouter(prefix="/security", tags=["security"])

DEFAULT_BUILDING = "BLD-HQ-01"


@router.post("/ingest")
def ingest(db: Session = Depends(get_db)):
    """Milestone 3: integrate access-control monitoring data. See
    data/build_security_dataset.py for the full honesty disclosure — this
    is a synthetic-but-disclosed dataset with injected labeled anomalies."""
    try:
        result = security_service.ingest_events(db)
    except FileNotFoundError as e:
        raise HTTPException(503, str(e))
    return {"status": "ok", "building_id": DEFAULT_BUILDING, **result}


@router.get("/building")
def building(building_id: str = Query(DEFAULT_BUILDING), db: Session = Depends(get_db)):
    """Single call that powers the security dashboard: building summary,
    flagged events, access points, and top alerts."""
    agent = SecurityAgent(db, building_id)
    result = agent.run()
    analysis = result["analysis"]
    return {
        "building_id": building_id,
        "building": analysis["building"],
        "flagged_events": analysis["flagged_events"],
        "access_points": analysis["access_points"],
        "heatmap": analysis["heatmap"],
        "access_point_activity": analysis["access_point_activity"],
        "top_alerts": result["recommendations"][:8],
        "model_confidence": get_model_confidence(),
        "comparison_model_confidence": get_comparison_model_confidence(),
        "supervised_reference_confidence": get_supervised_reference_confidence(),
        "data_drift": get_data_drift(security_service.get_recent_events_df(db)),
    }


@router.get("/access-points")
def access_points(building_id: str = Query(DEFAULT_BUILDING), db: Session = Depends(get_db)):
    aps = security_service.list_access_points(db, building_id)
    return {
        "building_id": building_id,
        "access_points": [{"access_point_id": a.access_point_id, "name": a.name, "zone_id": a.zone_id, "risk_level": a.risk_level} for a in aps],
    }


@router.get("/events")
def events(limit: int = Query(200, le=1000), db: Session = Depends(get_db)):
    """Recent raw access events (for the access timeline)."""
    df = security_service.get_recent_events_df(db, limit=limit)
    if df.empty:
        return {"events": []}
    return {"events": df.drop(columns=["is_anomaly_ground_truth", "anomaly_type_ground_truth"], errors="ignore").to_dict(orient="records")}


@router.get("/alerts")
def alerts(building_id: str = Query(DEFAULT_BUILDING), status: str | None = Query(None), db: Session = Depends(get_db)):
    """All security alerts, including ones created via the Occupancy
    Agent's cross-agent handoff (source='occupancy_agent')."""
    return {"building_id": building_id, "alerts": security_service.list_alerts(db, building_id, status)}


@router.get("/investigate")
def investigate(building_id: str = Query(DEFAULT_BUILDING)):
    """Genuinely agentic endpoint: the model decides which flagged events
    warrant a real alert, weighing anomaly score against access-point risk."""
    return investigate_security(building_id)


# --- Manual dataset management (add / view / remove individual events) ---

# --- Manual dataset management (add / view / remove individual events) ---

SECURITY_ALIASES = {
    "access_point_id": ["access_point_id", "access_point", "door_id", "door"],
    "employee_id": ["employee_id", "employee", "badge_id", "user_id"],
    "timestamp": ["timestamp", "date", "datetime", "time"],
    "access_granted": ["access_granted", "granted", "success", "allowed"],
}


def _to_bool(v):
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("1", "true", "yes", "granted", "allowed", "y")


@router.post("/ingest/upload")
async def ingest_upload(
    file: UploadFile = File(...),
    replace: bool = Query(True, description="Clear existing events before loading this file"),
    db: Session = Depends(get_db),
):
    """Upload your own access-event CSV/Excel for the existing access-point
    roster. Column names auto-detected (access_point_id, employee_id,
    timestamp, access_granted). The Isolation Forest anomaly model,
    heatmap, and risk grid all re-score from whatever lands in the table."""
    tmp_path = save_upload_tmp(file)
    try:
        df = read_any(tmp_path)
        resolved = resolve_columns(df, SECURITY_ALIASES, required={"access_point_id", "employee_id"})

        known_aps = {a.access_point_id: a for a in db.query(AccessPoint).all()}
        unknown = set(df[resolved["access_point_id"]].astype(str).unique()) - set(known_aps)
        if unknown:
            raise HTTPException(
                400,
                f"Unknown access_point_id value(s) {sorted(unknown)[:5]} — this building's access points are: {sorted(known_aps)[:10]}. "
                f"Upload events for existing access points, or re-run /security/ingest first to load a fresh roster.",
            )

        out = pd.DataFrame()
        out["access_point_id"] = df[resolved["access_point_id"]].astype(str)
        out["employee_id"] = df[resolved["employee_id"]].astype(str)
        out["timestamp"] = pd.to_datetime(df[resolved["timestamp"]]) if "timestamp" in resolved else pd.Timestamp.utcnow()
        out["access_granted"] = df[resolved["access_granted"]].map(_to_bool) if "access_granted" in resolved else True
        out = out.dropna(subset=["access_point_id", "employee_id"])

        if replace:
            for ap_id in out["access_point_id"].unique():
                db.query(AccessEvent).filter(AccessEvent.access_point_id == ap_id).delete()

        rows = [AccessEvent(
            event_id=f"upload-{uuid.uuid4().hex[:10]}", access_point_id=r.access_point_id,
            employee_id=r.employee_id, timestamp=r.timestamp, access_granted=bool(r.access_granted),
            risk_level=known_aps[r.access_point_id].risk_level,
        ) for r in out.itertuples(index=False)]
        db.bulk_save_objects(rows)
        db.commit()
        return {"status": "ok", "rows_ingested": len(rows), "access_points_affected": sorted(out["access_point_id"].unique().tolist())}
    except ValueError as e:
        raise HTTPException(400, str(e))
    finally:
        tmp_path.unlink(missing_ok=True)


class AccessEventIn(BaseModel):
    access_point_id: str
    employee_id: str
    timestamp: datetime | None = None
    access_granted: bool = True


@router.get("/records/recent")
def recent_records(access_point_id: str | None = Query(None), limit: int = Query(20, le=200), db: Session = Depends(get_db)):
    """Most recent N raw access events, for the dataset-management table."""
    q = db.query(AccessEvent)
    if access_point_id:
        q = q.filter(AccessEvent.access_point_id == access_point_id)
    rows = q.order_by(AccessEvent.timestamp.desc()).limit(limit).all()
    return {"records": [{
        "id": r.id, "event_id": r.event_id, "access_point_id": r.access_point_id,
        "employee_id": r.employee_id, "timestamp": r.timestamp,
        "access_granted": r.access_granted, "risk_level": r.risk_level,
    } for r in rows]}


@router.post("/records")
def add_record(payload: AccessEventIn, db: Session = Depends(get_db), current_user: User = Depends(require_role("admin", "technician"))):
    """Add one manual access event."""
    ap = db.query(AccessPoint).filter(AccessPoint.access_point_id == payload.access_point_id).first()
    if not ap:
        raise HTTPException(404, f"Unknown access_point_id {payload.access_point_id}")
    row = AccessEvent(
        event_id=f"manual-{uuid.uuid4().hex[:10]}",
        access_point_id=payload.access_point_id,
        employee_id=payload.employee_id,
        timestamp=payload.timestamp or datetime.utcnow(),
        access_granted=payload.access_granted,
        risk_level=ap.risk_level,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"status": "ok", "id": row.id}


@router.delete("/records/{record_id}")
def delete_record(record_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role("admin", "technician"))):
    """Remove one access event by id."""
    row = db.query(AccessEvent).filter(AccessEvent.id == record_id).first()
    if not row:
        raise HTTPException(404, "Event not found")
    db.delete(row)
    db.commit()
    return {"status": "ok", "deleted_id": record_id}


@router.delete("/records")
def clear_all_records(access_point_id: str | None = Query(None), db: Session = Depends(get_db), current_user: User = Depends(require_role("admin", "technician"))):
    """Wipe every access event — or just one door's, if access_point_id is
    given — with no replacement loaded."""
    q = db.query(AccessEvent)
    if access_point_id:
        q = q.filter(AccessEvent.access_point_id == access_point_id)
    deleted = q.delete()
    db.commit()
    return {"status": "ok", "deleted_count": deleted}
