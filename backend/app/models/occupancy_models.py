from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from app.core.database import Base


class Zone(Base):
    """One row = one monitored facility zone (open floor, meeting room,
    cafeteria, lobby, restricted area...). Populated by the occupancy
    ingestion pipeline (Milestone 3)."""
    __tablename__ = "occupancy_zones"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(String, index=True, nullable=False)
    zone_id = Column(String, index=True, nullable=False, unique=True)
    name = Column(String, nullable=False)
    zone_type = Column(String, nullable=False)  # workspace | meeting_room | common_area | restricted
    capacity = Column(Integer, nullable=False)


class ZoneReading(Base):
    """One row = one headcount snapshot for a zone at a given timestamp.
    See data/build_occupancy_dataset.py for how this is derived — a real
    day-of-week/time-of-day profile from the UCI Occupancy Detection
    dataset, projected onto multiple named zones (disclosed synthetic
    split, same honesty pattern as Energy's submeter split)."""
    __tablename__ = "occupancy_readings"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)
    headcount = Column(Integer, nullable=False)
    utilization_pct = Column(Float, nullable=False)

    __table_args__ = (
        Index("ix_occ_zone_ts", "zone_id", "timestamp"),
    )
