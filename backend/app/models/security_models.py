from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Index
from app.core.database import Base


class AccessPoint(Base):
    """One row = one monitored door/entry point."""
    __tablename__ = "security_access_points"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(String, index=True, nullable=False)
    access_point_id = Column(String, index=True, nullable=False, unique=True)
    name = Column(String, nullable=False)
    zone_id = Column(String, nullable=True)  # links to occupancy_zones.zone_id where applicable
    risk_level = Column(String, nullable=False)  # low | medium | high


class AccessEvent(Base):
    """One row = one badge/access attempt. See
    data/build_security_dataset.py for the full honesty disclosure — this
    is a synthetic-but-disclosed dataset with injected labeled anomalies,
    NOT a real security incident log."""
    __tablename__ = "security_access_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, index=True, nullable=False, unique=True)
    access_point_id = Column(String, index=True, nullable=False)
    employee_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)
    access_granted = Column(Boolean, nullable=False)
    risk_level = Column(String, nullable=False)

    # Ground truth from the synthetic generator — kept ONLY for honest
    # offline model evaluation (see ml_models/security/train_anomaly_model.py).
    # The live detector never reads these two columns at inference time.
    is_anomaly_ground_truth = Column(Boolean, nullable=True)
    anomaly_type_ground_truth = Column(String, nullable=True)

    __table_args__ = (
        Index("ix_sec_ap_ts", "access_point_id", "timestamp"),
        Index("ix_sec_emp_ts", "employee_id", "timestamp"),
    )


class SecurityAlert(Base):
    """A security alert / flagged incident. Created by the Security
    Agent's own anomaly detector, OR by a cross-agent handoff (the
    Occupancy Agent flagging a restricted zone that shows unexpected
    headcount) — `source` records which agent actually created it, same
    auditability pattern as MaintenanceEvent."""
    __tablename__ = "security_alerts"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(String, index=True, nullable=False)
    access_point_id = Column(String, nullable=True)
    zone_id = Column(String, nullable=True)
    employee_id = Column(String, nullable=True)
    source = Column(String, nullable=False)  # "security_agent" | "occupancy_agent"
    alert_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)  # low | medium | high
    description = Column(String, nullable=False)
    status = Column(String, default="open", nullable=False)  # open | resolved
    created_at = Column(DateTime, nullable=False)
