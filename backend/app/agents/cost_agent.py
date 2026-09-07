"""
Cost Optimization Agent (Milestone 4).

Same template as Energy/Maintenance/Occupancy/Security. analyze() pulls
together the anomaly-flagged invoices (ML), the spend trend forecast
(ML), budget compliance (rule-based, against assumption-based budgets —
see data/build_cost_dataset.py), and vendor concentration (rule-based).
recommend() turns the clearest of those into actionable recommendations,
mirroring Security's "don't alert on every flag" discipline.
"""
from sqlalchemy.orm import Session

from app.services import cost_service
from app.utils.cost_analytics import (
    score_records, top_flagged_records, forecast_trend, budget_compliance,
    vendor_concentration, spend_summary, category_breakdown,
)

ANOMALY_SCORE_THRESHOLD = 0.55
VENDOR_CONCENTRATION_WARNING_PCT = 60.0


class CostAgent:
    def __init__(self, db: Session, building_id: str = "BLD-HQ-01"):
        self.db = db
        self.building_id = building_id
        self.vendors = cost_service.list_vendors(db, building_id)
        self.budgets = cost_service.list_budgets(db, building_id)

    def analyze(self) -> dict:
        records = cost_service.get_records_df(self.db, self.building_id)
        scored = score_records(records)
        vendors_meta = [{
            "vendor_id": v.vendor_id, "vendor_name": v.vendor_name, "primary_category": v.primary_category,
            "order_count": v.order_count, "total_spend_inr": v.total_spend_inr,
        } for v in self.vendors]
        budgets_meta = [{"category": b.category, "monthly_budget_inr": b.monthly_budget_inr, "basis": b.basis} for b in self.budgets]

        return {
            "summary": spend_summary(records),
            "category_breakdown": category_breakdown(records),
            "flagged_invoices": top_flagged_records(scored, limit=20),
            "forecast": forecast_trend(records),
            "budget_compliance": budget_compliance(records, budgets_meta),
            "vendor_concentration": vendor_concentration(vendors_meta),
        }

    def recommend(self, analysis: dict | None = None) -> list[dict]:
        analysis = analysis or self.analyze()
        recs = []

        for b in analysis["budget_compliance"]:
            if b["status"] == "over":
                recs.append({
                    "id": f"REC-COST-BUDGET-{b['category'].replace(' ', '_')}",
                    "title": f"{b['category']} over its assumption-based monthly budget",
                    "category": "budget_compliance",
                    "severity": "high" if b["pct_of_budget"] > 130 else "medium",
                    "description": (
                        f"{b['category']} spent ₹{b['spent_inr']:,.0f} this month against a "
                        f"budget of ₹{b['budget_inr']:,.0f} ({b['pct_of_budget']}%). Budget basis: {b['basis']}"
                    ),
                })

        for rec in analysis["flagged_invoices"]:
            if rec["anomaly_score"] < ANOMALY_SCORE_THRESHOLD:
                continue
            recs.append({
                "id": f"REC-COST-{rec['record_id']}",
                "title": f"Unusual invoice flagged: {rec['vendor_name']}",
                "category": "anomaly_detection",
                "severity": "high" if rec["anomaly_score"] > 0.75 else "medium",
                "description": (
                    f"₹{rec['amount_inr']:,.2f} invoice from {rec['vendor_name']} ({rec['category']}) "
                    f"scored {rec['anomaly_score']} on the anomaly detector — statistically unusual "
                    "for this vendor/category pattern. Worth a second look, not a confirmed error."
                ),
            })

        conc = analysis["vendor_concentration"]
        if conc["top_n_share_pct"] >= VENDOR_CONCENTRATION_WARNING_PCT:
            recs.append({
                "id": "REC-COST-VENDOR-CONCENTRATION",
                "title": "High vendor concentration risk",
                "category": "vendor_optimization",
                "severity": "medium",
                "description": (
                    f"Top {len(conc['top_vendors'])} vendors account for {conc['top_n_share_pct']}% of "
                    f"total tracked spend (₹{conc['total_spend_inr']:,.0f}). Consider diversifying "
                    "suppliers for the largest categories to reduce single-vendor dependency risk."
                ),
            })

        severity_rank = {"high": 0, "medium": 1, "low": 2}
        recs.sort(key=lambda r: severity_rank[r["severity"]])
        return recs

    def run(self) -> dict:
        analysis = self.analyze()
        recommendations = self.recommend(analysis)
        return {"building_id": self.building_id, "analysis": analysis, "recommendations": recommendations}
