from sqlalchemy import Column, Integer, String, Float, DateTime, Index, Boolean
from app.core.database import Base


class Asset(Base):
    """
    One row = one piece of monitored facility equipment (chiller, AHU, pump,
    compressor, cooling tower...). Populated by the maintenance ingestion
    pipeline (Milestone 2: asset monitoring data integration).
    """
    __tablename__ = "maintenance_assets"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(String, index=True, nullable=False)
    asset_id = Column(String, index=True, nullable=False, unique=True)
    name = Column(String, nullable=False)
    asset_type = Column(String, nullable=False)
    location = Column(String, nullable=True)
    commissioned_at = Column(DateTime, nullable=True)


class AssetReading(Base):
    """
    One row = one sensor snapshot for an asset at a given operating cycle.
    `cycle` is the asset's own operating-cycle counter (mirrors the source
    dataset's run-to-failure cycle index); `timestamp` maps that cycle onto
    a wall-clock date (1 cycle = 1 operating day, anchored so the most
    recent cycle is "today" — same anchoring approach as the Energy
    module's dataset).
    """
    __tablename__ = "maintenance_readings"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(String, index=True, nullable=False)
    cycle = Column(Integer, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)

    # Sensor channels (relabeled generically from the source dataset's
    # physical sensors — see backend/data/build_maintenance_dataset.py and
    # README for the honest mapping/caveat).
    temp_stage1_c = Column(Float, nullable=True)
    temp_stage2_c = Column(Float, nullable=True)
    temp_stage3_c = Column(Float, nullable=True)
    pressure_kpa = Column(Float, nullable=True)
    vibration_index = Column(Float, nullable=True)
    flow_rate = Column(Float, nullable=True)
    efficiency_ratio = Column(Float, nullable=True)
    bleed_load = Column(Float, nullable=True)

    # Only present for training-source assets (full run-to-failure history);
    # null for live/current fleet assets, whose true RUL is unknown — that's
    # exactly what the ML model is for.
    true_rul_cycles = Column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_maint_asset_cycle", "asset_id", "cycle"),
    )


class MaintenanceEvent(Base):
    """
    A maintenance alert / work order. Created either by the Maintenance
    Agent's own rule+ML engine, OR by a cross-agent handoff (the Energy
    Agent's flag_for_maintenance_review tool calling
    maintenance_service.open_work_order for real — see ARCHITECTURE.md).
    `source` records which agent actually created it, so the handoff is
    auditable rather than just implied.
    """
    __tablename__ = "maintenance_events"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(String, index=True, nullable=False)
    asset_id = Column(String, index=True, nullable=False)
    source = Column(String, nullable=False)  # "maintenance_agent" | "energy_agent" | "rule_engine"
    reason = Column(String, nullable=False)
    severity = Column(String, nullable=False)  # low | medium | high
    status = Column(String, default="open", nullable=False)  # open | resolved
    created_at = Column(DateTime, nullable=False)
