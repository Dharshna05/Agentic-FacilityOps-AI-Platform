"""
Data ingestion service.

Milestone 1 requirement: "Integrate utility and IoT data."
For local dev this reads a file (CSV or Excel) that stands in for a
utility/IoT feed. In production this is the seam where you'd swap in a
real connector: a utility API poller, an MQTT subscriber for IoT meters,
a Modbus/BACnet gateway, etc. Everything downstream (Energy Agent,
analytics, dashboard) only depends on rows landing in EnergyReading, so
swapping the source here doesn't ripple.

Supports two shapes of input file:
  1. Our own schema (building_id, sensor_id, timestamp, total_kwh, ...)
     — the default, produced by backend/data/build_dataset.py
  2. An external/teammate dataset with looser column names (e.g. a Kaggle
     export: "date", "Power Consumption", "Outdoor Temperature",
     "Occupancy") — auto-detected and normalized by _normalize_external_df.
"""
import pandas as pd
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.config import settings
from app.models.energy_models import EnergyReading

DEFAULT_BUILDING_ID = "BLD-HQ-01"
DEFAULT_SENSOR_ID = "MAIN-METER-01"

# Submeter load-share ratios, same as build_dataset.py, applied when a
# source file only has a single total power column (no submeters).
SUBMETER_SHARES = {"hvac_kwh": 0.40, "lighting_kwh": 0.20, "plug_load_kwh": 0.25, "other_kwh": 0.15}

# Flexible column-name matching for external files (case/spacing tolerant)
COLUMN_ALIASES = {
    "timestamp": ["date", "timestamp", "datetime", "date/time", "time"],
    "total_kwh": ["power consumption", "total_kwh", "power_kw", "energy_usage", "power consumption(kw)", "kwh"],
    "outdoor_temp_c": ["outdoor temperature", "outdoor_temp_c", "temperature", "temp", "temp (c)"],
    "occupancy_count": ["occupancy", "occupancy_count", "occupancy_level", "headcount"],
}


def _read_any(path: Path) -> pd.DataFrame:
    """Read a CSV or Excel file transparently based on extension."""
    suffix = Path(path).suffix.lower()
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(path)
    return pd.read_csv(path)


def _looks_like_our_schema(df: pd.DataFrame) -> bool:
    return {"building_id", "sensor_id", "timestamp", "total_kwh"}.issubset(set(df.columns))


def _normalize_external_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Map a loosely-formatted external dataset (e.g. a teammate's Kaggle
    export) onto our internal schema. Derives submeters from the total
    using standard load-share ratios if they aren't already present.
    """
    lower_map = {c.lower().strip(): c for c in df.columns}
    resolved = {}
    for target, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lower_map:
                resolved[target] = lower_map[alias]
                break

    missing = {"timestamp", "total_kwh"} - set(resolved)
    if missing:
        raise ValueError(
            f"Could not find required column(s) {missing} in the source file. "
            f"Available columns: {list(df.columns)}"
        )

    out = pd.DataFrame()
    out["timestamp"] = pd.to_datetime(df[resolved["timestamp"]])
    out["total_kwh"] = pd.to_numeric(df[resolved["total_kwh"]], errors="coerce")
    out["outdoor_temp_c"] = pd.to_numeric(df[resolved["outdoor_temp_c"]], errors="coerce") if "outdoor_temp_c" in resolved else None
    out["occupancy_count"] = pd.to_numeric(df[resolved["occupancy_count"]], errors="coerce") if "occupancy_count" in resolved else None

    out = out.dropna(subset=["timestamp", "total_kwh"])

    for col, share in SUBMETER_SHARES.items():
        out[col] = (out["total_kwh"] * share).round(2)

    out["building_id"] = DEFAULT_BUILDING_ID
    out["sensor_id"] = DEFAULT_SENSOR_ID

    return out


def _load_and_normalize(path: Path) -> pd.DataFrame:
    df = _read_any(path)
    if _looks_like_our_schema(df):
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    return _normalize_external_df(df)


def ingest_from_csv(db: Session, csv_path=None) -> int:
    """Load readings from the configured file (CSV or Excel) into the DB.
    Idempotent-ish for demo purposes: clears existing rows for the same
    building before reloading, so re-running ingestion doesn't duplicate data.
    """
    path = csv_path or settings.ENERGY_RAW_CSV
    df = _load_and_normalize(Path(path))

    building_id = df["building_id"].iloc[0]
    db.query(EnergyReading).filter(EnergyReading.building_id == building_id).delete()

    records = [
        EnergyReading(
            building_id=row.building_id,
            sensor_id=row.sensor_id,
            timestamp=row.timestamp,
            total_kwh=row.total_kwh,
            hvac_kwh=row.hvac_kwh,
            lighting_kwh=row.lighting_kwh,
            plug_load_kwh=row.plug_load_kwh,
            other_kwh=row.other_kwh,
            outdoor_temp_c=getattr(row, "outdoor_temp_c", None),
            occupancy_count=getattr(row, "occupancy_count", None),
        )
        for row in df.itertuples(index=False)
    ]
    db.bulk_save_objects(records)
    db.commit()
    return len(records)


def get_readings_df(db: Session, building_id: str) -> pd.DataFrame:
    """Pull readings for a building back out as a DataFrame for analytics."""
    q = (
        db.query(EnergyReading)
        .filter(EnergyReading.building_id == building_id)
        .order_by(EnergyReading.timestamp)
    )
    rows = [
        {
            "timestamp": r.timestamp,
            "total_kwh": r.total_kwh,
            "hvac_kwh": r.hvac_kwh,
            "lighting_kwh": r.lighting_kwh,
            "plug_load_kwh": r.plug_load_kwh,
            "other_kwh": r.other_kwh,
            "outdoor_temp_c": r.outdoor_temp_c,
            "occupancy_count": r.occupancy_count,
        }
        for r in q.all()
    ]
    return pd.DataFrame(rows)


def has_data(db: Session, building_id: str) -> bool:
    count = (
        db.query(func.count(EnergyReading.id))
        .filter(EnergyReading.building_id == building_id)
        .scalar()
    )
    return bool(count)
