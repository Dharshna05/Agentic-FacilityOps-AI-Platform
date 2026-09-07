"""
Occupancy data service. Same "file-as-stand-in-for-a-real-feed" seam as
Energy/Maintenance's services — swap ingest_zones() for a real badge-reader
or people-counter feed in production without touching anything downstream.
"""
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.occupancy_models import Zone, ZoneReading

DEFAULT_BUILDING_ID = "BLD-HQ-01"
PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
ZONES_CSV = PROCESSED_DIR / "occupancy_zones.csv"
READINGS_CSV = PROCESSED_DIR / "occupancy_zone_readings.csv"


def ingest_zones(db: Session, zones_csv: Path = ZONES_CSV, readings_csv: Path = READINGS_CSV, building_id: str = DEFAULT_BUILDING_ID) -> dict:
    if not zones_csv.exists() or not readings_csv.exists():
        raise FileNotFoundError(
            f"Occupancy dataset not built yet. Run: python data/build_occupancy_dataset.py (looked for {zones_csv})"
        )

    zones_df = pd.read_csv(zones_csv)
    readings_df = pd.read_csv(readings_csv, parse_dates=["timestamp"])

    db.query(ZoneReading).delete()
    db.query(Zone).delete()

    zone_rows = [
        Zone(
            building_id=building_id,
            zone_id=row.zone_id,
            name=row.name,
            zone_type=row.zone_type,
            capacity=int(row.capacity),
        )
        for row in zones_df.itertuples(index=False)
    ]
    db.bulk_save_objects(zone_rows)

    reading_rows = [
        ZoneReading(
            zone_id=row.zone_id,
            timestamp=row.timestamp,
            headcount=int(row.headcount),
            utilization_pct=float(row.utilization_pct),
        )
        for row in readings_df.itertuples(index=False)
    ]
    db.bulk_save_objects(reading_rows)
    db.commit()

    return {"zones_ingested": len(zone_rows), "readings_ingested": len(reading_rows)}


def has_data(db: Session, building_id: str = DEFAULT_BUILDING_ID) -> bool:
    count = db.query(func.count(Zone.id)).filter(Zone.building_id == building_id).scalar()
    return bool(count)


def list_zones(db: Session, building_id: str = DEFAULT_BUILDING_ID) -> list[Zone]:
    return db.query(Zone).filter(Zone.building_id == building_id).all()


def get_zone(db: Session, zone_id: str) -> Zone | None:
    return db.query(Zone).filter(Zone.zone_id == zone_id).first()


def get_readings_df(db: Session, zone_id: str, limit: int = 500) -> pd.DataFrame:
    rows = (
        db.query(ZoneReading)
        .filter(ZoneReading.zone_id == zone_id)
        .order_by(ZoneReading.timestamp.desc())
        .limit(limit)
        .all()
    )
    rows = list(reversed(rows))
    return pd.DataFrame([{
        "timestamp": r.timestamp,
        "headcount": r.headcount,
        "utilization_pct": r.utilization_pct,
    } for r in rows])


def get_latest_readings_df(db: Session, building_id: str = DEFAULT_BUILDING_ID) -> pd.DataFrame:
    """One row per zone — its most recent reading, joined with zone metadata."""
    zones = list_zones(db, building_id)
    frames = []
    for z in zones:
        df = get_readings_df(db, z.zone_id, limit=1)
        if df.empty:
            continue
        latest = df.iloc[[-1]].copy()
        latest["zone_id"] = z.zone_id
        latest["name"] = z.name
        latest["zone_type"] = z.zone_type
        latest["capacity"] = z.capacity
        frames.append(latest)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
