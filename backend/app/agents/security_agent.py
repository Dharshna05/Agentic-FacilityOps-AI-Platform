"""
Security Agent (Milestone 3).

Same template as the other three agents. analyze() runs the live anomaly
detector against the recent event stream; recommend() turns the highest-
confidence flags into actionable alerts, weighting by access-point risk
level so a flagged event at the Server Room door outranks the same anomaly
score at the Main Entrance.
"""
from sqlalchemy.orm import Session

from app.services import security_service
from app.utils.security_analytics import (
    score_events, building_security_summary, top_flagged_events,
    access_point_heatmap, access_point_activity,
)

# Anomaly scores below this are technically "flagged" by the Isolation
# Forest but too weak to page a human about — keeps the alert list focused
# on the events worth a look, consistent with the honest precision/recall
# numbers in model_metrics.json (this isn't a perfect detector).
ALERT_SCORE_THRESHOLD = 0.55


class SecurityAgent:
    def __init__(self, db: Session, building_id: str = "BLD-HQ-01"):
        self.db = db
        self.building_id = building_id
        self.access_points = security_service.list_access_points(db, building_id)

    def analyze(self) -> dict:
        events = security_service.get_recent_events_df(self.db, limit=3000)
        first_visit_map = security_service.get_first_visit_timestamps(self.db)
        scored = score_events(events, first_visit_map)
        ap_meta = [{"access_point_id": a.access_point_id, "name": a.name, "risk_level": a.risk_level} for a in self.access_points]
        return {
            "building": building_security_summary(scored, ap_meta),
            "flagged_events": top_flagged_events(scored, limit=20),
            "access_points": ap_meta,
            "heatmap": access_point_heatmap(scored, ap_meta),
            "access_point_activity": access_point_activity(scored, ap_meta),
        }

    def recommend(self, analysis: dict | None = None) -> list[dict]:
        analysis = analysis or self.analyze()
        flagged = analysis["flagged_events"]
        ap_by_id = {a["access_point_id"]: a for a in analysis["access_points"]}
        recs = []

        for ev in flagged:
            if ev["anomaly_score"] < ALERT_SCORE_THRESHOLD:
                continue
            ap = ap_by_id.get(ev["access_point_id"], {})
            risk = ap.get("risk_level", "low")
            severity = "high" if (risk == "high" or ev["anomaly_score"] > 0.75) else "medium" if risk == "medium" else "low"
            recs.append({
                "id": f"REC-SEC-{ev['event_id']}",
                "title": f"Anomalous access flagged: {ap.get('name', ev['access_point_id'])}",
                "category": "anomaly_detection",
                "severity": severity,
                "access_point_id": ev["access_point_id"],
                "employee_id": ev["employee_id"],
                "description": (
                    f"Badge event by {ev['employee_id']} at {ap.get('name', ev['access_point_id'])} "
                    f"({'granted' if ev['access_granted'] else 'DENIED'}) scored {ev['anomaly_score']} "
                    "on the anomaly detector — statistically unusual timing/pattern for this access "
                    f"point (risk level: {risk}). Recommend review."
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
