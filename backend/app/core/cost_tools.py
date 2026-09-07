"""
Tools available to the Cost Agent's agentic investigation loop — same
pattern as app/core/security_tools.py.
"""
from app.core.database import SessionLocal
from app.services import cost_service
from app.utils.cost_analytics import (
    score_records, top_flagged_records, forecast_trend, budget_compliance,
    vendor_concentration, spend_summary,
)


def get_spend_summary(building_id: str = "BLD-HQ-01") -> dict:
    """Get total tracked facility spend: total ₹, number of invoices,
    number of vendors, number of cost categories, and the date range
    covered.

    Args:
        building_id: The building identifier, e.g. "BLD-HQ-01".
    """
    db = SessionLocal()
    try:
        records = cost_service.get_records_df(db, building_id)
        return spend_summary(records)
    finally:
        db.close()


def get_budget_compliance(building_id: str = "BLD-HQ-01") -> list:
    """Get current-month actual spend vs. budget for every cost
    category, sorted by how close to (or over) budget each is. Budgets
    are assumption-based (documented in the response's 'basis' field) —
    weigh that when deciding how urgently to act.

    Args:
        building_id: The building identifier, e.g. "BLD-HQ-01".
    """
    db = SessionLocal()
    try:
        records = cost_service.get_records_df(db, building_id)
        budgets = [{"category": b.category, "monthly_budget_inr": b.monthly_budget_inr, "basis": b.basis} for b in cost_service.list_budgets(db, building_id)]
        return budget_compliance(records, budgets)
    finally:
        db.close()


def get_flagged_invoices(building_id: str = "BLD-HQ-01", min_score: float = 0.5) -> list:
    """Get recent invoices the anomaly detector flagged as statistically
    unusual for their vendor/category, sorted by anomaly score (highest
    first). No labeled ground truth exists for this real invoice data —
    treat a flag as a lead worth checking, not a confirmed error.

    Args:
        building_id: The building identifier, e.g. "BLD-HQ-01".
        min_score: Only return invoices with anomaly_score at or above this (0+ range, higher = more unusual).
    """
    db = SessionLocal()
    try:
        records = cost_service.get_records_df(db, building_id)
        scored = score_records(records)
        flagged = top_flagged_records(scored, limit=30)
        return [f for f in flagged if f["anomaly_score"] >= min_score]
    finally:
        db.close()


def get_spend_forecast(building_id: str = "BLD-HQ-01") -> dict:
    """Get the ML model's forecast for the facility's forward 3-week
    average spend trend (up/down/flat), plus the model's own honest
    accuracy metrics. Only 27 weeks of real training data — factor the
    reported confidence into how much weight you give this.

    Args:
        building_id: The building identifier, e.g. "BLD-HQ-01".
    """
    db = SessionLocal()
    try:
        records = cost_service.get_records_df(db, building_id)
        return forecast_trend(records)
    finally:
        db.close()


def get_vendor_concentration(building_id: str = "BLD-HQ-01") -> dict:
    """Get what share of total tracked spend sits with the top 5
    vendors — a high share signals single-supplier dependency risk.

    Args:
        building_id: The building identifier, e.g. "BLD-HQ-01".
    """
    db = SessionLocal()
    try:
        vendors = [{
            "vendor_id": v.vendor_id, "vendor_name": v.vendor_name, "primary_category": v.primary_category,
            "order_count": v.order_count, "total_spend_inr": v.total_spend_inr,
        } for v in cost_service.list_vendors(db, building_id)]
        return vendor_concentration(vendors)
    finally:
        db.close()


def create_cost_alert(alert_type: str, description: str, severity: str = "medium", category: str | None = None, vendor_id: str | None = None) -> dict:
    """Open a real cost-optimization alert. Use this when you've found
    clear evidence (a category clearly over budget, or a high-confidence
    flagged invoice at a concentrated vendor) — not for every data point
    you merely check.

    Args:
        alert_type: Short label for the kind of issue, e.g. "budget_overrun" or "invoice_anomaly".
        description: A concise explanation of what was found and why it warrants an alert.
        severity: One of "low", "medium", "high".
        category: The cost category involved, if applicable.
        vendor_id: The vendor ID involved, if applicable.
    """
    db = SessionLocal()
    try:
        return cost_service.open_alert(
            db, alert_type=alert_type, description=description, severity=severity,
            source="cost_agent", category=category, vendor_id=vendor_id,
        )
    finally:
        db.close()


ALL_TOOLS = [
    get_spend_summary,
    get_budget_compliance,
    get_flagged_invoices,
    get_spend_forecast,
    get_vendor_concentration,
    create_cost_alert,
]
