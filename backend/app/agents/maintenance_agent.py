"""
Maintenance Agent (Milestone 2).

Follows the exact template established by EnergyAgent (see
ARCHITECTURE.md): __init__ pulls the data it needs, analyze() runs
domain-specific analytics (here: per-asset ML health scoring + fleet
rollups), recommend() turns that into ranked, actionable alerts (rule-based
AND ML-driven), and run() is the single entrypoint the API/other agents call.
"""
from sqlalchemy.orm import Session

from app.services import maintenance_service
from app.utils.maintenance_analytics import score_asset, fleet_summary, risk_ranking


class MaintenanceAgent:
    def __init__(self, db: Session, building_id: str = "BLD-HQ-01"):
        self.db = db
        self.building_id = building_id
        self.assets = maintenance_service.list_assets(db, building_id)

    # ---- Analysis -------------------------------------------------
    def analyze(self) -> dict:
        scored = []
        for asset in self.assets:
            readings = maintenance_service.get_readings_df(self.db, asset.asset_id)
            if readings.empty:
                continue
            meta = {
                "asset_id": asset.asset_id, "name": asset.name,
                "asset_type": asset.asset_type, "location": asset.location,
            }
            scored.append(score_asset(meta, readings))

        return {
            "assets": scored,
            "fleet": fleet_summary(scored),
            "risk_ranking": risk_ranking(scored, limit=10),
        }

    # ---- Recommendations -------------------------------------------
    def recommend(self, analysis: dict | None = None) -> list[dict]:
        analysis = analysis or self.analyze()
        assets = analysis["assets"]
        fleet = analysis["fleet"]
        recs = []

        # Rule 1: any Critical asset -> immediate work order (ML-driven:
        # this fires off the model's predicted RUL/health score, not a
        # fixed sensor threshold).
        for a in assets:
            if a["status"] == "Critical":
                recs.append({
                    "id": f"REC-MAINT-CRITICAL-{a['asset_id']}",
                    "title": f"Immediate maintenance required: {a['name']}",
                    "category": "critical",
                    "severity": "high",
                    "asset_id": a["asset_id"],
                    "predicted_maintenance_date": a["predicted_maintenance_date"],
                    "description": (
                        f"{a['name']} ({a['asset_type']}, {a['location']}) has a predicted health "
                        f"score of {a['health_score']}/100 — ML model estimates only "
                        f"{a['predicted_rul_cycles']} operating days of remaining useful life "
                        f"(model confidence: {a['confidence'].get('confidence', 'n/a')}). "
                        "Schedule inspection immediately."
                    ),
                })

        # Rule 2: Warning status + actively worsening trend -> schedule
        # preventive maintenance before it becomes Critical.
        for a in assets:
            if a["status"] == "Warning" and a["trend"].get("direction") == "worsening":
                recs.append({
                    "id": f"REC-MAINT-WARN-{a['asset_id']}",
                    "title": f"Schedule preventive maintenance: {a['name']}",
                    "category": "preventive",
                    "severity": "medium",
                    "asset_id": a["asset_id"],
                    "predicted_maintenance_date": a["predicted_maintenance_date"],
                    "description": (
                        f"{a['name']} is in Warning status (health {a['health_score']}/100) and its "
                        f"vibration signature is actively worsening (slope "
                        f"{a['trend']['vibration_slope_per_cycle']}/cycle). Predicted maintenance "
                        f"window: around {a['predicted_maintenance_date'].strftime('%Y-%m-%d') if hasattr(a['predicted_maintenance_date'], 'strftime') else a['predicted_maintenance_date']}. "
                        "Scheduling now avoids an unplanned failure."
                    ),
                })

        # Rule 3: fleet-wide systemic signal — a large fraction of the
        # fleet degraded at once often means a shared cause (bad batch,
        # environmental factor) rather than N unrelated failures.
        if fleet["assets_monitored"] > 0:
            degraded_pct = fleet["status_pct"].get("Warning", 0) + fleet["status_pct"].get("Critical", 0)
            if degraded_pct >= 30:
                recs.append({
                    "id": "REC-MAINT-FLEETWIDE-01",
                    "title": "Investigate fleet-wide degradation pattern",
                    "category": "systemic",
                    "severity": "high" if degraded_pct >= 50 else "medium",
                    "asset_id": None,
                    "description": (
                        f"{degraded_pct}% of monitored assets are currently in Warning or Critical "
                        "status simultaneously. This is unusual enough to suggest a shared root cause "
                        "(e.g. a bad maintenance batch, extreme operating conditions, or a supply/parts "
                        "issue) rather than independent random failures — worth investigating at the "
                        "fleet level before dispatching individual work orders."
                    ),
                })

        # Rule 4: Good status but trend already worsening -> early
        # monitoring flag, cheapest intervention point.
        for a in assets:
            if a["status"] == "Good" and a["trend"].get("direction") == "worsening":
                recs.append({
                    "id": f"REC-MAINT-MONITOR-{a['asset_id']}",
                    "title": f"Increase monitoring frequency: {a['name']}",
                    "category": "monitoring",
                    "severity": "low",
                    "asset_id": a["asset_id"],
                    "predicted_maintenance_date": a["predicted_maintenance_date"],
                    "description": (
                        f"{a['name']} is still Good ({a['health_score']}/100) but its wear indicator "
                        "has started trending upward. No action needed yet — flagging for closer "
                        "tracking so this doesn't reach Warning unnoticed."
                    ),
                })

        severity_rank = {"high": 0, "medium": 1, "low": 2}
        recs.sort(key=lambda r: severity_rank[r["severity"]])
        return recs

    # ---- Entry point -------------------------------------------------
    def run(self) -> dict:
        analysis = self.analyze()
        recommendations = self.recommend(analysis)
        return {
            "building_id": self.building_id,
            "analysis": analysis,
            "recommendations": recommendations,
        }
