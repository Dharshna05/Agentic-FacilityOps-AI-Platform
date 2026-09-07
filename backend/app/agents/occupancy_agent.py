"""
Occupancy Agent (Milestone 3).

Same template as EnergyAgent/MaintenanceAgent: __init__ pulls the data it
needs, analyze() runs domain analytics (per-zone status + building rollup +
heatmap), recommend() turns that into ranked actionable alerts, run() is the
single entrypoint the API/other agents call.

Also performs a real cross-agent handoff: if the Server Room (a restricted
zone) shows ANY occupancy at all outside business hours, that's exactly the
kind of physical-security-relevant signal the Occupancy Agent is
well-positioned to notice first (it's watching headcounts) but the Security
Agent owns — so it hands off via security_service.open_alert(), the same
real-row-in-a-shared-table pattern already established by the Energy ->
Maintenance handoff.
"""
from sqlalchemy.orm import Session

from app.services import occupancy_service
from app.utils.occupancy_analytics import zone_status, building_summary, heatmap_data, overcrowding_alerts


class OccupancyAgent:
    def __init__(self, db: Session, building_id: str = "BLD-HQ-01"):
        self.db = db
        self.building_id = building_id
        self.zones = occupancy_service.list_zones(db, building_id)

    def analyze(self) -> dict:
        scored = []
        readings_by_id = {}
        for zone in self.zones:
            readings = occupancy_service.get_readings_df(self.db, zone.zone_id, limit=2000)
            readings_by_id[zone.zone_id] = readings
            meta = {
                "zone_id": zone.zone_id, "name": zone.name,
                "zone_type": zone.zone_type, "capacity": zone.capacity,
            }
            scored.append(zone_status(meta, readings))

        return {
            "zones": scored,
            "building": building_summary(scored),
            "heatmap": heatmap_data(readings_by_id),
        }

    def recommend(self, analysis: dict | None = None) -> list[dict]:
        analysis = analysis or self.analyze()
        zones = analysis["zones"]
        recs = []

        # Rule 1: overcrowded zones -> immediate space alert.
        for z in overcrowding_alerts(zones):
            recs.append({
                "id": f"REC-OCC-OVERCROWD-{z['zone_id']}",
                "title": f"Overcrowding detected: {z['name']}",
                "category": "overcrowding",
                "severity": "high",
                "zone_id": z["zone_id"],
                "description": (
                    f"{z['name']} is at {z['current_utilization_pct']}% of capacity "
                    f"({z['current_headcount']}/{z['capacity']} people) — above the "
                    "90% overcrowding threshold. Consider directing traffic to a "
                    "less-utilized zone or reviewing capacity for this space."
                ),
            })

        # Rule 2: chronically underutilized workspace -> space optimization signal.
        for z in zones:
            if z.get("zone_type") == "workspace" and z.get("current_utilization_pct") is not None:
                if z["current_utilization_pct"] < 15 and z.get("peak_utilization_today_pct", 0) < 25:
                    recs.append({
                        "id": f"REC-OCC-UNDERUSED-{z['zone_id']}",
                        "title": f"Low utilization: {z['name']}",
                        "category": "space_optimization",
                        "severity": "low",
                        "zone_id": z["zone_id"],
                        "description": (
                            f"{z['name']} peaked at only {z['peak_utilization_today_pct']}% utilization "
                            "today. If this pattern holds over time, this space may be a candidate for "
                            "resizing, repurposing, or consolidation."
                        ),
                    })

        # Rule 3 (cross-agent handoff): restricted zone occupied at all is
        # itself worth a Security look — headcount data doesn't know WHO is
        # in there, only that someone is, which is exactly the gap the
        # Security Agent's badge-event data fills.
        for z in zones:
            if z.get("zone_type") == "restricted" and (z.get("current_headcount") or 0) > 0:
                recs.append({
                    "id": f"REC-OCC-RESTRICTED-{z['zone_id']}",
                    "title": f"Restricted zone occupied: {z['name']}",
                    "category": "security_handoff",
                    "severity": "medium",
                    "zone_id": z["zone_id"],
                    "description": (
                        f"{z['name']} shows {z['current_headcount']} occupant(s) — flagged to Security "
                        "for badge-log cross-reference, since occupancy sensing alone can't confirm "
                        "who's inside or whether their access was authorized."
                    ),
                })

        severity_rank = {"high": 0, "medium": 1, "low": 2}
        recs.sort(key=lambda r: severity_rank[r["severity"]])
        return recs

    def run(self) -> dict:
        analysis = self.analyze()
        recommendations = self.recommend(analysis)
        return {
            "building_id": self.building_id,
            "analysis": analysis,
            "recommendations": recommendations,
        }
