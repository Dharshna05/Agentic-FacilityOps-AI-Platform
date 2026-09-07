"""
Tools available to the Occupancy Agent's agentic investigation loop — same
pattern as app/core/maintenance_tools.py.
"""
from app.core.database import SessionLocal
from app.services import occupancy_service, security_service
from app.utils.occupancy_analytics import zone_status, building_summary, overcrowding_alerts


def get_building_occupancy_summary(building_id: str = "BLD-HQ-01") -> dict:
    """Get building-wide occupancy: how many zones are monitored, total
    headcount, average utilization, and how many zones are currently
    overcrowded.

    Args:
        building_id: The building identifier, e.g. "BLD-HQ-01".
    """
    db = SessionLocal()
    try:
        zones = occupancy_service.list_zones(db, building_id)
        scored = []
        for z in zones:
            readings = occupancy_service.get_readings_df(db, z.zone_id, limit=500)
            meta = {"zone_id": z.zone_id, "name": z.name, "zone_type": z.zone_type, "capacity": z.capacity}
            scored.append(zone_status(meta, readings))
        return building_summary(scored)
    finally:
        db.close()


def get_zone_status(zone_id: str) -> dict:
    """Get the current status for one specific zone: headcount, utilization
    percent, status bucket (Low/Moderate/Busy/Overcrowded), and today's peak.

    Args:
        zone_id: The zone identifier, e.g. "ZN-01".
    """
    db = SessionLocal()
    try:
        zone = occupancy_service.get_zone(db, zone_id)
        if not zone:
            return {"error": f"zone {zone_id} not found"}
        readings = occupancy_service.get_readings_df(db, zone_id, limit=500)
        meta = {"zone_id": zone.zone_id, "name": zone.name, "zone_type": zone.zone_type, "capacity": zone.capacity}
        return zone_status(meta, readings)
    finally:
        db.close()


def get_overcrowded_zones(building_id: str = "BLD-HQ-01") -> list:
    """Get all zones currently over the 90% utilization threshold, worth a
    closer look or a space-management action.

    Args:
        building_id: The building identifier, e.g. "BLD-HQ-01".
    """
    db = SessionLocal()
    try:
        zones = occupancy_service.list_zones(db, building_id)
        scored = []
        for z in zones:
            readings = occupancy_service.get_readings_df(db, z.zone_id, limit=500)
            meta = {"zone_id": z.zone_id, "name": z.name, "zone_type": z.zone_type, "capacity": z.capacity}
            scored.append(zone_status(meta, readings))
        return overcrowding_alerts(scored)
    finally:
        db.close()


def get_restricted_zone_status(building_id: str = "BLD-HQ-01") -> list:
    """Get the current status of every RESTRICTED zone (e.g. server rooms)
    specifically — the zones worth checking for a Security handoff even
    when they're nowhere near the general overcrowding threshold, since a
    restricted zone showing ANY occupancy is unusual by definition.

    Args:
        building_id: The building identifier, e.g. "BLD-HQ-01".
    """
    db = SessionLocal()
    try:
        zones = occupancy_service.list_zones(db, building_id)
        out = []
        for z in zones:
            if z.zone_type != "restricted":
                continue
            readings = occupancy_service.get_readings_df(db, z.zone_id, limit=500)
            meta = {"zone_id": z.zone_id, "name": z.name, "zone_type": z.zone_type, "capacity": z.capacity}
            out.append(zone_status(meta, readings))
        return out
    finally:
        db.close()


def flag_restricted_zone_for_security_review(zone_id: str, reason: str, severity: str = "medium") -> dict:
    """Hand off a restricted-zone occupancy concern to the Security Agent by
    opening a real security alert. Use this ONLY for zone_type='restricted'
    zones showing occupancy that badge-log cross-reference should verify —
    occupancy sensing alone can't confirm WHO is present.

    Args:
        zone_id: The restricted zone's identifier, e.g. "ZN-07".
        reason: A concise explanation of what was observed and why it warrants security review.
        severity: One of "low", "medium", "high".
    """
    db = SessionLocal()
    try:
        return security_service.open_alert(
            db, alert_type="restricted_zone_occupancy", description=reason,
            severity=severity, source="occupancy_agent", zone_id=zone_id,
        )
    finally:
        db.close()


ALL_TOOLS = [
    get_building_occupancy_summary,
    get_zone_status,
    get_overcrowded_zones,
    get_restricted_zone_status,
    flag_restricted_zone_for_security_review,
]
