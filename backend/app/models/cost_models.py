from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from app.core.database import Base


class CostVendor(Base):
    """One row = one vendor. See data/build_cost_dataset.py for the full
    honesty disclosure — see data/build_cost_dataset.py for the full picture: real BBMP (Bengaluru)
    open data), mapped onto this building as a stand-in facility."""
    __tablename__ = "cost_vendors"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(String, index=True, nullable=False)
    vendor_id = Column(String, index=True, nullable=False, unique=True)
    vendor_name = Column(String, nullable=False)
    primary_category = Column(String, nullable=False)
    order_count = Column(Integer, nullable=False)
    total_spend_inr = Column(Float, nullable=False)


class CostRecord(Base):
    """One row = one real invoice line item (see honesty disclosure in
    data/build_cost_dataset.py)."""
    __tablename__ = "cost_records"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(String, index=True, nullable=False, unique=True)
    building_id = Column(String, index=True, nullable=False)
    vendor_id = Column(String, index=True, nullable=False)
    vendor_name = Column(String, nullable=False)
    category = Column(String, index=True, nullable=False)
    date = Column(DateTime, index=True, nullable=False)
    amount_inr = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    po_number = Column(String, nullable=True)

    __table_args__ = (Index("ix_cost_cat_date", "category", "date"),)


class CostBudget(Base):
    """Assumption-based monthly budget ceiling per category — see
    data/build_cost_dataset.py's honesty disclosure. NOT a real published
    council budget."""
    __tablename__ = "cost_budgets"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(String, index=True, nullable=False)
    category = Column(String, index=True, nullable=False, unique=True)
    monthly_budget_inr = Column(Float, nullable=False)
    basis = Column(String, nullable=False)


class CostAlert(Base):
    """A cost-optimization alert / flagged finding. `source` records
    which agent created it — same auditability pattern as SecurityAlert
    and MaintenanceEvent."""
    __tablename__ = "cost_alerts"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(String, index=True, nullable=False)
    category = Column(String, nullable=True)
    vendor_id = Column(String, nullable=True)
    record_id = Column(String, nullable=True)
    source = Column(String, nullable=False, default="cost_agent")
    alert_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)  # low | medium | high
    description = Column(String, nullable=False)
    status = Column(String, default="open", nullable=False)  # open | resolved
    created_at = Column(DateTime, nullable=False)
