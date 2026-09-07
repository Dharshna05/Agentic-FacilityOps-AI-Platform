"""
Cost data service. Same seam pattern as Energy/Maintenance/Occupancy/
Security — ingest_records() loads the processed dataset built by
data/build_cost_dataset.py (see that file for the full honesty
disclosure: real BBMP (Bengaluru) capital-works data + logically-derived
building as a stand-in facility).

open_alert() is the real implementation behind cost alerts, same
cross-agent-handoff-ready pattern as security_service.open_alert /
maintenance_service.open_work_order.
"""
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.cost_models import CostVendor, CostRecord, CostBudget, CostAlert

DEFAULT_BUILDING_ID = "BLD-HQ-01"
PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
RECORDS_CSV = PROCESSED_DIR / "cost_records.csv"
VENDORS_CSV = PROCESSED_DIR / "cost_vendors.csv"
BUDGETS_CSV = PROCESSED_DIR / "cost_budgets.csv"


def ingest_records(
    db: Session,
    records_csv: Path = RECORDS_CSV,
    vendors_csv: Path = VENDORS_CSV,
    budgets_csv: Path = BUDGETS_CSV,
    building_id: str = DEFAULT_BUILDING_ID,
) -> dict:
    if not records_csv.exists() or not vendors_csv.exists() or not budgets_csv.exists():
        raise FileNotFoundError(
            f"Cost dataset not built yet. Run: python data/build_cost_dataset.py (looked for {records_csv})"
        )

    records_df = pd.read_csv(records_csv, parse_dates=["date"])
    vendors_df = pd.read_csv(vendors_csv)
    budgets_df = pd.read_csv(budgets_csv)

    db.query(CostRecord).delete()
    db.query(CostVendor).delete()
    db.query(CostBudget).delete()

    vendor_rows = [
        CostVendor(
            building_id=building_id, vendor_id=row.vendor_id, vendor_name=row.vendor_name,
            primary_category=row.primary_category, order_count=int(row.order_count),
            total_spend_inr=float(row.total_spend_inr),
        )
        for row in vendors_df.itertuples(index=False)
    ]
    db.bulk_save_objects(vendor_rows)

    record_rows = [
        CostRecord(
            record_id=row.record_id, building_id=building_id, vendor_id=row.vendor_id,
            vendor_name=row.vendor_name, category=row.category, date=row.date,
            amount_inr=float(row.amount_inr),
            description=None if pd.isna(row.description) else row.description,
            po_number=None if pd.isna(row.po_number) else str(row.po_number),
        )
        for row in records_df.itertuples(index=False)
    ]
    db.bulk_save_objects(record_rows)

    budget_rows = [
        CostBudget(
            building_id=building_id, category=row.category,
            monthly_budget_inr=float(row.monthly_budget_inr), basis=row.basis,
        )
        for row in budgets_df.itertuples(index=False)
    ]
    db.bulk_save_objects(budget_rows)

    db.commit()
    return {"records_ingested": len(record_rows), "vendors_ingested": len(vendor_rows), "budgets_ingested": len(budget_rows)}


def has_data(db: Session, building_id: str = DEFAULT_BUILDING_ID) -> bool:
    count = db.query(func.count(CostRecord.id)).filter(CostRecord.building_id == building_id).scalar()
    return bool(count)


def get_records_df(db: Session, building_id: str = DEFAULT_BUILDING_ID) -> pd.DataFrame:
    rows = db.query(CostRecord).filter(CostRecord.building_id == building_id).order_by(CostRecord.date).all()
    df = pd.DataFrame([{
        "record_id": r.record_id, "vendor_id": r.vendor_id, "vendor_name": r.vendor_name,
        "category": r.category, "date": r.date, "amount_inr": r.amount_inr,
        "description": r.description, "po_number": r.po_number,
    } for r in rows])
    if not df.empty:
        # po_number is genuinely NULL for every derived_cross_agent record
        # (no PO exists for an internal cost estimate) — pandas' string
        # dtype can surface that as float NaN rather than None, which
        # isn't valid JSON. Normalize to None so /cost/records never 500s.
        df["po_number"] = df["po_number"].astype(object).where(df["po_number"].notna(), None)
    return df


def list_vendors(db: Session, building_id: str = DEFAULT_BUILDING_ID) -> list[CostVendor]:
    return db.query(CostVendor).filter(CostVendor.building_id == building_id).order_by(CostVendor.total_spend_inr.desc()).all()


def list_budgets(db: Session, building_id: str = DEFAULT_BUILDING_ID) -> list[CostBudget]:
    return db.query(CostBudget).filter(CostBudget.building_id == building_id).all()


# ---- Alerts (the real cross-agent handoff target) ----------------------

def open_alert(
    db: Session,
    alert_type: str,
    description: str,
    severity: str = "medium",
    source: str = "cost_agent",
    category: str | None = None,
    vendor_id: str | None = None,
    record_id: str | None = None,
    building_id: str = DEFAULT_BUILDING_ID,
) -> dict:
    alert = CostAlert(
        building_id=building_id, category=category, vendor_id=vendor_id, record_id=record_id,
        source=source, alert_type=alert_type, severity=severity, description=description,
        status="open", created_at=datetime.now(),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return {
        "id": alert.id, "alert_type": alert.alert_type, "source": alert.source,
        "severity": alert.severity, "description": alert.description, "status": alert.status,
        "created_at": alert.created_at, "category": alert.category,
        "vendor_id": alert.vendor_id, "record_id": alert.record_id,
    }


def list_alerts(db: Session, building_id: str = DEFAULT_BUILDING_ID, status: str | None = None) -> list[dict]:
    q = db.query(CostAlert).filter(CostAlert.building_id == building_id)
    if status:
        q = q.filter(CostAlert.status == status)
    alerts = q.order_by(CostAlert.created_at.desc()).all()
    return [{
        "id": a.id, "alert_type": a.alert_type, "source": a.source, "severity": a.severity,
        "description": a.description, "status": a.status, "created_at": a.created_at,
        "category": a.category, "vendor_id": a.vendor_id, "record_id": a.record_id,
    } for a in alerts]
