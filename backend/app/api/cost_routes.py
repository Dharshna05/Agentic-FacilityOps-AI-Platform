from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import uuid
import pandas as pd

from app.core.database import get_db
from app.core.security import require_role
from app.models.auth_models import User
from app.core.intelligence_engine import investigate_cost
from app.services import cost_service
from app.agents.cost_agent import CostAgent
from app.utils.cost_analytics import get_anomaly_model_confidence, get_anomaly_comparison_confidence, get_forecast_confidence, get_data_drift
from app.utils.csv_upload import read_any, resolve_columns, save_upload_tmp
from app.models.cost_models import CostRecord, CostVendor

router = APIRouter(prefix="/cost", tags=["cost"])

DEFAULT_BUILDING = "BLD-HQ-01"


@router.post("/ingest")
def ingest(db: Session = Depends(get_db)):
    """Milestone 4: integrate facility cost data. Combines real BBMP
    (Bengaluru) capital-works tender data with cross-agent-derived
    operational cost, both in INR. See data/build_cost_dataset.py for
    the full honesty disclosure."""
    try:
        result = cost_service.ingest_records(db)
    except FileNotFoundError as e:
        raise HTTPException(503, str(e))
    return {"status": "ok", "building_id": DEFAULT_BUILDING, **result}


@router.get("/building")
def building(building_id: str = Query(DEFAULT_BUILDING), db: Session = Depends(get_db)):
    """Single call that powers the cost dashboard: spend summary,
    category breakdown, flagged invoices, forecast, budget compliance,
    and vendor concentration."""
    agent = CostAgent(db, building_id)
    result = agent.run()
    analysis = result["analysis"]
    return {
        "building_id": building_id,
        "summary": analysis["summary"],
        "category_breakdown": analysis["category_breakdown"],
        "flagged_invoices": analysis["flagged_invoices"],
        "forecast": analysis["forecast"],
        "budget_compliance": analysis["budget_compliance"],
        "vendor_concentration": analysis["vendor_concentration"],
        "recommendations": result["recommendations"][:8],
        "anomaly_model_confidence": get_anomaly_model_confidence(),
        "anomaly_comparison_confidence": get_anomaly_comparison_confidence(),
        "forecast_confidence": get_forecast_confidence(),
        "data_drift": get_data_drift(cost_service.get_records_df(db)),
    }


@router.get("/vendors")
def vendors(building_id: str = Query(DEFAULT_BUILDING), db: Session = Depends(get_db)):
    vs = cost_service.list_vendors(db, building_id)
    return {"building_id": building_id, "vendors": [{
        "vendor_id": v.vendor_id, "vendor_name": v.vendor_name, "primary_category": v.primary_category,
        "order_count": v.order_count, "total_spend_inr": v.total_spend_inr,
    } for v in vs]}


@router.get("/budgets")
def budgets(building_id: str = Query(DEFAULT_BUILDING), db: Session = Depends(get_db)):
    bs = cost_service.list_budgets(db, building_id)
    return {"building_id": building_id, "budgets": [{
        "category": b.category, "monthly_budget_inr": b.monthly_budget_inr, "basis": b.basis,
    } for b in bs]}


@router.get("/records")
def records(limit: int = Query(200, le=1000), db: Session = Depends(get_db)):
    df = cost_service.get_records_df(db)
    if df.empty:
        return {"records": []}
    return {"records": df.tail(limit).to_dict(orient="records")}


@router.get("/alerts")
def alerts(building_id: str = Query(DEFAULT_BUILDING), status: str | None = Query(None), db: Session = Depends(get_db)):
    return {"building_id": building_id, "alerts": cost_service.list_alerts(db, building_id, status)}


@router.get("/investigate")
def investigate(building_id: str = Query(DEFAULT_BUILDING)):
    """Genuinely agentic endpoint: the model decides which budget risks,
    flagged invoices, or vendor-concentration signals warrant a real alert."""
    return investigate_cost(building_id)


# --- Manual dataset management (add / view / remove individual records) ---

COST_ALIASES = {
    "vendor_name": ["vendor_name", "vendor", "supplier", "supplier_name"],
    "category": ["category", "cost_category"],
    "date": ["date", "timestamp", "document_date"],
    "amount_inr": ["amount_inr", "amount", "value", "net_order_value"],
    "description": ["description", "notes", "desc"],
}


@router.post("/ingest/upload")
async def ingest_upload(
    file: UploadFile = File(...),
    replace: bool = Query(True, description="Clear existing records before loading this file"),
    db: Session = Depends(get_db),
):
    """Upload your own spend CSV/Excel. Column names auto-detected
    (vendor_name, category, date, amount_inr, description). New vendors
    are created automatically; the anomaly/forecast models re-score from
    whatever lands in the table."""
    tmp_path = save_upload_tmp(file)
    try:
        df = read_any(tmp_path)
        resolved = resolve_columns(df, COST_ALIASES, required={"vendor_name", "amount_inr"})

        out = pd.DataFrame()
        out["vendor_name"] = df[resolved["vendor_name"]].astype(str)
        out["category"] = df[resolved["category"]].astype(str) if "category" in resolved else "Repairs & Maintenance"
        out["date"] = pd.to_datetime(df[resolved["date"]]) if "date" in resolved else pd.Timestamp.utcnow()
        out["amount_inr"] = pd.to_numeric(df[resolved["amount_inr"]], errors="coerce")
        out["description"] = df[resolved["description"]].astype(str) if "description" in resolved else None
        out = out.dropna(subset=["vendor_name", "amount_inr"])

        if replace:
            db.query(CostRecord).delete()

        known_vendors = {v.vendor_name: v.vendor_id for v in db.query(CostVendor).all()}
        rows = []
        for r in out.itertuples(index=False):
            vendor_id = known_vendors.get(r.vendor_name)
            if not vendor_id:
                vendor_id = f"VEND-UPLOAD-{uuid.uuid4().hex[:6]}"
                db.add(CostVendor(building_id=DEFAULT_BUILDING, vendor_id=vendor_id, vendor_name=r.vendor_name, primary_category=r.category, order_count=0, total_spend_inr=0.0))
                known_vendors[r.vendor_name] = vendor_id
            rows.append(CostRecord(
                record_id=f"upload-{uuid.uuid4().hex[:10]}", building_id=DEFAULT_BUILDING, vendor_id=vendor_id,
                vendor_name=r.vendor_name, category=r.category, date=r.date, amount_inr=float(r.amount_inr),
                description=r.description,
            ))
        db.bulk_save_objects(rows)
        db.commit()
        return {"status": "ok", "rows_ingested": len(rows)}
    except ValueError as e:
        raise HTTPException(400, str(e))
    finally:
        tmp_path.unlink(missing_ok=True)


class CostRecordIn(BaseModel):
    vendor_name: str
    category: str = "Repairs & Maintenance"
    date: datetime | None = None
    amount_inr: float
    description: str | None = None


@router.get("/records/recent")
def recent_records(category: str | None = Query(None), limit: int = Query(20, le=200), db: Session = Depends(get_db)):
    """Most recent N raw cost records, for the dataset-management table."""
    q = db.query(CostRecord)
    if category:
        q = q.filter(CostRecord.category == category)
    rows = q.order_by(CostRecord.date.desc()).limit(limit).all()
    return {"records": [{
        "id": r.id, "record_id": r.record_id, "vendor_name": r.vendor_name, "category": r.category,
        "date": r.date, "amount_inr": r.amount_inr, "description": r.description,
    } for r in rows]}


@router.post("/records")
def add_record(payload: CostRecordIn, db: Session = Depends(get_db), current_user: User = Depends(require_role("admin", "technician"))):
    """Add one manual cost record."""
    vendor = db.query(CostVendor).filter(CostVendor.vendor_name == payload.vendor_name).first()
    vendor_id = vendor.vendor_id if vendor else f"VEND-MANUAL-{uuid.uuid4().hex[:6]}"
    if not vendor:
        db.add(CostVendor(building_id=DEFAULT_BUILDING, vendor_id=vendor_id, vendor_name=payload.vendor_name, primary_category=payload.category, order_count=0, total_spend_inr=0.0))
    row = CostRecord(
        record_id=f"manual-{uuid.uuid4().hex[:10]}", building_id=DEFAULT_BUILDING, vendor_id=vendor_id,
        vendor_name=payload.vendor_name, category=payload.category, date=payload.date or datetime.utcnow(),
        amount_inr=payload.amount_inr, description=payload.description,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"status": "ok", "id": row.id}


@router.delete("/records/{record_id}")
def delete_record(record_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role("admin", "technician"))):
    """Remove one cost record by id."""
    row = db.query(CostRecord).filter(CostRecord.id == record_id).first()
    if not row:
        raise HTTPException(404, "Record not found")
    db.delete(row)
    db.commit()
    return {"status": "ok", "deleted_id": record_id}


@router.delete("/records")
def clear_all_records(category: str | None = Query(None), db: Session = Depends(get_db), current_user: User = Depends(require_role("admin", "technician"))):
    """Wipe every cost record — or just one category's, if given."""
    q = db.query(CostRecord)
    if category:
        q = q.filter(CostRecord.category == category)
    deleted = q.delete()
    db.commit()
    return {"status": "ok", "deleted_count": deleted}
