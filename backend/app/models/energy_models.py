from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from app.core.database import Base


class EnergyReading(Base):
    """
    One row = one hourly reading from a facility's main meter + submeters.
    Populated by the ingestion pipeline (Milestone 1: utility/IoT integration).
    """
    __tablename__ = "energy_readings"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(String, index=True, nullable=False)
    sensor_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)

    total_kwh = Column(Float, nullable=False)
    hvac_kwh = Column(Float, default=0.0)
    lighting_kwh = Column(Float, default=0.0)
    plug_load_kwh = Column(Float, default=0.0)
    other_kwh = Column(Float, default=0.0)

    # Added for weather-normalized analytics and occupancy-aware recommendations
    outdoor_temp_c = Column(Float, nullable=True)
    occupancy_count = Column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_building_timestamp", "building_id", "timestamp"),
    )
