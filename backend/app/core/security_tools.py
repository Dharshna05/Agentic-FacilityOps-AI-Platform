"""
Tools available to the Security Agent's agentic investigation loop — same
pattern as app/core/maintenance_tools.py.
"""
from app.core.database import SessionLocal
from app.services import security_service
from app.utils.security_analytics import score_events, building_security_summary, top_flagged_events


def get_security_summary(building_id: str = "BLD-HQ-01") -> dict:
    """Get building-wide security status over the last 24 hours: access
    points monitored, total events, denied attempts, and how many events
    the anomaly detector flagged.

    Args:
        building_id: The building identifier, e.g. "BLD-HQ-01".
    """
    db = SessionLocal()
    try:
        access_points = security_service.list_access_points(db, building_id)
        events = security_service.get_recent_events_df(db, limit=3000)
        first_visit_map = security_service.get_first_visit_timestamps(db)
        scored = score_events(events, first_visit_map)
        ap_meta = [{"access_point_id": a.access_point_id, "name": a.name, "risk_level": a.risk_level} for a in access_points]
        return building_security_summary(scored, ap_meta)
    finally:
        db.close()


def get_flagged_events(building_id: str = "BLD-HQ-01", min_score: float = 0.5) -> list:
    """Get recent access events the anomaly detector flagged as unusual,
    sorted by anomaly score (highest first). Use this to decide which
    specific events deserve an alert.

    Args:
        building_id: The building identifier, e.g. "BLD-HQ-01".
        min_score: Only return events with anomaly_score at or above this (0-1 range, higher = more unusual).
    """
    db = SessionLocal()
    try:
        events = security_service.get_recent_events_df(db, limit=3000)
        first_visit_map = security_service.get_first_visit_timestamps(db)
        scored = score_events(events, first_visit_map)
        flagged = top_flagged_events(scored, limit=30)
        return [e for e in flagged if e["anomaly_score"] >= min_score]
    finally:
        db.close()


def get_access_point_risk(access_point_id: str) -> dict:
    """Get the configured risk level for a specific access point (e.g.
    server rooms are 'high' risk, main entrance is 'low').

    Args:
        access_point_id: The access point identifier, e.g. "AP-04".
    """
    db = SessionLocal()
    try:
        aps = security_service.list_access_points(db)
        for a in aps:
            if a.access_point_id == access_point_id:
                return {"access_point_id": a.access_point_id, "name": a.name, "risk_level": a.risk_level, "zone_id": a.zone_id}
        return {"error": f"access point {access_point_id} not found"}
    finally:
        db.close()


def create_security_alert(alert_type: str, description: str, severity: str = "medium", access_point_id: str | None = None, employee_id: str | None = None) -> dict:
    """Open a real security alert. Use this when you've found clear
    evidence (high anomaly score AND high-risk access point, or a
    repeated-denial pattern) — not for every flagged event you merely check.

    Args:
        alert_type: Short label for what kind of issue this is, e.g. "unauthorized_restricted_zone_access".
        description: A concise explanation of what was found and why it warrants an alert.
        severity: One of "low", "medium", "high".
        access_point_id: The access point involved, if applicable.
        employee_id: The badge/employee ID involved, if applicable.
    """
    db = SessionLocal()
    try:
        return security_service.open_alert(
            db, alert_type=alert_type, description=description, severity=severity,
            source="security_agent", access_point_id=access_point_id, employee_id=employee_id,
        )
    finally:
        db.close()


ALL_TOOLS = [
    get_security_summary,
    get_flagged_events,
    get_access_point_risk,
    create_security_alert,
]
