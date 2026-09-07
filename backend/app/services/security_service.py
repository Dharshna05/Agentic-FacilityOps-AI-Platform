"""
Security data service. Same seam pattern as Energy/Maintenance/Occupancy —
ingest_events() stands in for a real access-control system / VMS feed.

open_alert() is the real implementation behind security alerts — the
single function both the Security Agent's own detector AND the Occupancy
Agent's restricted-zone handoff call, so that cross-agent handoff creates
one real row in the same table regardless of which agent triggered it
(same pattern as maintenance_service.open_work_order).
"""
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.security_models import AccessPoint, AccessEvent, SecurityAlert

DEFAULT_BUILDING_ID = "BLD-HQ-01"
PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
EVENTS_CSV = PROCESSED_DIR / "security_access_events.csv"
ACCESS_POINTS_CSV = PROCESSED_DIR / "security_access_points.csv"


def ingest_events(db: Session, events_csv: Path = EVENTS_CSV, ap_csv: Path = ACCESS_POINTS_CSV, building_id: str = DEFAULT_BUILDING_ID) -> dict:
    if not events_csv.exists() or not ap_csv.exists():
        raise FileNotFoundError(
            f"Security dataset not built yet. Run: python data/build_security_dataset.py (looked for {events_csv})"
        )

    ap_df = pd.read_csv(ap_csv)
    events_df = pd.read_csv(events_csv, parse_dates=["timestamp"])

    db.query(AccessEvent).delete()
    db.query(AccessPoint).delete()

    ap_rows = [
        AccessPoint(
            building_id=building_id,
            access_point_id=row.access_point_id,
            name=row.name,
            zone_id=None if pd.isna(row.zone_id) else row.zone_id,
            risk_level=row.risk_level,
        )
        for row in ap_df.itertuples(index=False)
    ]
    db.bulk_save_objects(ap_rows)

    event_rows = [
        AccessEvent(
            event_id=row.event_id,
            access_point_id=row.access_point_id,
            employee_id=row.employee_id,
            timestamp=row.timestamp,
            access_granted=bool(row.access_granted),
            risk_level=row.risk_level,
            is_anomaly_ground_truth=bool(row.is_anomaly),
            anomaly_type_ground_truth=None if pd.isna(row.anomaly_type) else row.anomaly_type,
        )
        for row in events_df.itertuples(index=False)
    ]
    db.bulk_save_objects(event_rows)
    db.commit()

    return {"access_points_ingested": len(ap_rows), "events_ingested": len(event_rows)}


def has_data(db: Session, building_id: str = DEFAULT_BUILDING_ID) -> bool:
    count = db.query(func.count(AccessPoint.id)).filter(AccessPoint.building_id == building_id).scalar()
    return bool(count)


def list_access_points(db: Session, building_id: str = DEFAULT_BUILDING_ID) -> list[AccessPoint]:
    return db.query(AccessPoint).filter(AccessPoint.building_id == building_id).all()


def get_recent_events_df(db: Session, limit: int = 3000) -> pd.DataFrame:
    rows = db.query(AccessEvent).order_by(AccessEvent.timestamp.desc()).limit(limit).all()
    rows = list(reversed(rows))
    return pd.DataFrame([{
        "event_id": r.event_id,
        "access_point_id": r.access_point_id,
        "employee_id": r.employee_id,
        "timestamp": r.timestamp,
        "access_granted": r.access_granted,
        "risk_level": r.risk_level,
        "is_anomaly_ground_truth": r.is_anomaly_ground_truth,
        "anomaly_type_ground_truth": r.anomaly_type_ground_truth,
    } for r in rows])


def get_first_visit_timestamps(db: Session) -> dict:
    """Earliest timestamp per (employee_id, access_point_id) pair, across
    the FULL event history — not just the recent window get_recent_events_df
    returns. The anomaly model's "is this employee's first-ever visit to
    this door" feature needs the true first visit; computing "novelty" only
    from a recent 3000-row window would wrongly call routine, long-standing
    access patterns "novel" just because their real first visit fell
    outside the window. One cheap aggregate query, not a full table scan
    into pandas.
    """
    rows = (
        db.query(AccessEvent.employee_id, AccessEvent.access_point_id, func.min(AccessEvent.timestamp))
        .group_by(AccessEvent.employee_id, AccessEvent.access_point_id)
        .all()
    )
    return {(emp, ap): ts for emp, ap, ts in rows}


# ---- Alerts (the real cross-agent handoff target) ---------------------

def open_alert(
    db: Session,
    alert_type: str,
    description: str,
    severity: str = "medium",
    source: str = "security_agent",
    access_point_id: str | None = None,
    zone_id: str | None = None,
    employee_id: str | None = None,
    building_id: str = DEFAULT_BUILDING_ID,
) -> dict:
    alert = SecurityAlert(
        building_id=building_id,
        access_point_id=access_point_id,
        zone_id=zone_id,
        employee_id=employee_id,
        source=source,
        alert_type=alert_type,
        severity=severity,
        description=description,
        status="open",
        created_at=datetime.now(),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return {
        "id": alert.id, "alert_type": alert.alert_type, "source": alert.source,
        "severity": alert.severity, "description": alert.description,
        "status": alert.status, "created_at": alert.created_at,
        "access_point_id": alert.access_point_id, "zone_id": alert.zone_id, "employee_id": alert.employee_id,
    }


def list_alerts(db: Session, building_id: str = DEFAULT_BUILDING_ID, status: str | None = None) -> list[dict]:
    q = db.query(SecurityAlert).filter(SecurityAlert.building_id == building_id)
    if status:
        q = q.filter(SecurityAlert.status == status)
    alerts = q.order_by(SecurityAlert.created_at.desc()).all()
    return [{
        "id": a.id, "alert_type": a.alert_type, "source": a.source, "severity": a.severity,
        "description": a.description, "status": a.status, "created_at": a.created_at,
        "access_point_id": a.access_point_id, "zone_id": a.zone_id, "employee_id": a.employee_id,
    } for a in alerts]
