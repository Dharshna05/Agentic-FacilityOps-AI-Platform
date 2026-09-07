"""
Milestone 3 — live multi-zone occupancy dataset builder.

The UCI Occupancy Detection dataset (see train_occupancy_model.py) is real,
but it's a SINGLE room. A facility has many zones — open floors, meeting
rooms, a cafeteria, a lobby — so this script derives a real day-of-week /
time-of-day occupancy PROFILE from that single real room (exactly how
build_dataset.py already did for the Energy module's occupancy_count
column), then projects that same real shape onto several named zones, each
with its own capacity and independent noise.

This is a disclosed synthetic step, not a claim that we have real
multi-room sensor data — the underlying daily rhythm (quiet at night, rising
through the morning, lunch dip, afternoon peak, evening drop) is real and
extracted from actual sensor recordings; only the per-zone headcount split
is generated. Same honesty pattern already established for the Energy
module's submeter split and the Maintenance module's live fleet.
"""
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

np.random.seed(11)

RAW_DIR = Path(__file__).resolve().parent / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent / "processed"

N_DAYS = 21
FREQ = "15min"

ZONES = [
    {"zone_id": "ZN-01", "name": "Open Office - Floor 1", "zone_type": "workspace", "capacity": 80},
    {"zone_id": "ZN-02", "name": "Open Office - Floor 2", "zone_type": "workspace", "capacity": 80},
    {"zone_id": "ZN-03", "name": "Meeting Room A", "zone_type": "meeting_room", "capacity": 12},
    {"zone_id": "ZN-04", "name": "Meeting Room B", "zone_type": "meeting_room", "capacity": 8},
    {"zone_id": "ZN-05", "name": "Cafeteria", "zone_type": "common_area", "capacity": 60},
    {"zone_id": "ZN-06", "name": "Lobby", "zone_type": "common_area", "capacity": 30},
    {"zone_id": "ZN-07", "name": "Server Room", "zone_type": "restricted", "capacity": 4},
    {"zone_id": "ZN-08", "name": "Executive Wing", "zone_type": "workspace", "capacity": 15},
]

# Relative shape multipliers so different zone TYPES don't all just scale
# the same office curve identically — a cafeteria peaks at lunch harder
# than an open office does, a meeting room is bursty rather than smooth,
# the server room stays near-empty almost always.
TYPE_PROFILE_SHAPE = {
    "workspace": {"lunch_dip": 0.35, "noise_std": 0.06, "weekend_floor": 0.03},
    "meeting_room": {"lunch_dip": 0.15, "noise_std": 0.22, "weekend_floor": 0.0},
    "common_area": {"lunch_dip": -0.6, "noise_std": 0.10, "weekend_floor": 0.02},  # negative = lunch SPIKE
    "restricted": {"lunch_dip": 0.0, "noise_std": 0.30, "weekend_floor": 0.01},
}


def build():
    occ_frames = [pd.read_csv(RAW_DIR / f"occ_{f}") for f in ("datatraining.csv", "datatest.csv", "datatest2.csv")]
    occ = pd.concat(occ_frames, ignore_index=True)
    occ["minute_of_day"] = (occ["NSM"] // 60).astype(int)
    occ["bin_of_day"] = occ["minute_of_day"] // 15
    # Real base profile: fraction of 15-min bins, by weekday/weekend, where
    # the real room was occupied.
    profile = occ.groupby(["WeekStatus", "bin_of_day"])["Occupancy"].mean().to_dict()

    end_anchor = pd.Timestamp(datetime.now()).floor("h")
    start_anchor = end_anchor - timedelta(days=N_DAYS)
    index = pd.date_range(start_anchor, end_anchor, freq=FREQ)

    rows = []
    for zone in ZONES:
        shape = TYPE_PROFILE_SHAPE[zone["zone_type"]]
        for ts in index:
            is_weekday = int(ts.dayofweek < 5)
            bin_of_day = (ts.hour * 60 + ts.minute) // 15
            base_fraction = profile.get((is_weekday, bin_of_day), 0.0)

            # Lunch-hour adjustment (12:00-13:30): workspaces/meeting rooms
            # dip, common areas spike (negative dip = spike, see table above).
            hour = ts.hour + ts.minute / 60
            if 12.0 <= hour <= 13.5:
                base_fraction = np.clip(base_fraction * (1 - shape["lunch_dip"]) + (0.5 if shape["lunch_dip"] < 0 else 0), 0, 1)

            if not is_weekday:
                base_fraction = max(base_fraction, 0) * 0.15 + shape["weekend_floor"]

            noise = np.random.normal(0, shape["noise_std"])
            fraction = np.clip(base_fraction + noise, 0, 1)
            headcount = int(round(fraction * zone["capacity"]))

            rows.append({
                "zone_id": zone["zone_id"],
                "name": zone["name"],
                "zone_type": zone["zone_type"],
                "capacity": zone["capacity"],
                "timestamp": ts,
                "headcount": headcount,
                "utilization_pct": round(100 * headcount / zone["capacity"], 1),
            })

    df = pd.DataFrame(rows)
    PROCESSED_DIR.mkdir(exist_ok=True)
    df.to_csv(PROCESSED_DIR / "occupancy_zone_readings.csv", index=False)

    zones_df = pd.DataFrame(ZONES)
    zones_df.to_csv(PROCESSED_DIR / "occupancy_zones.csv", index=False)

    print(f"Rows: {len(df)}  Zones: {len(ZONES)}  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(df.groupby("zone_id")["utilization_pct"].mean().round(1))
    return df


if __name__ == "__main__":
    build()
