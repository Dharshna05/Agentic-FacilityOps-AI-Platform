from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class EnergyReadingOut(BaseModel):
    timestamp: datetime
    total_kwh: float
    hvac_kwh: float
    lighting_kwh: float
    plug_load_kwh: float
    other_kwh: float

    class Config:
        from_attributes = True


class IngestResponse(BaseModel):
    status: str
    rows_ingested: int
    building_id: str
    source: str


class ConsumptionSummary(BaseModel):
    period: str
    total_kwh: float
    avg_hourly_kwh: float
    peak_kwh: float
    peak_timestamp: Optional[datetime]
    min_kwh: float
    min_timestamp: Optional[datetime]


class SubmeterBreakdown(BaseModel):
    hvac_kwh: float
    lighting_kwh: float
    plug_load_kwh: float
    other_kwh: float
    hvac_pct: float
    lighting_pct: float
    plug_load_pct: float
    other_pct: float


class AnomalyOut(BaseModel):
    timestamp: datetime
    total_kwh: float
    expected_kwh: float
    z_score: float
    severity: str


class Recommendation(BaseModel):
    id: str
    title: str
    category: str
    severity: str  # low | medium | high
    estimated_savings_pct: float
    description: str


class DashboardSummary(BaseModel):
    building_id: str
    consumption: ConsumptionSummary
    breakdown: SubmeterBreakdown
    trend_pct_vs_prev_period: float
    anomaly_count: int
    top_recommendations: list[Recommendation]
