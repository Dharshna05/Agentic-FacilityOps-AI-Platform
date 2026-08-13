"""
Builds the Maintenance module's dataset from a REAL public source: NASA's
C-MAPSS Turbofan Engine Degradation Simulation dataset (Saxena & Goebel,
2008), FD001 subset — obtained via the GitHub mirror
github.com/edwardzjl/CMAPSSData (raw files committed at
backend/data/raw_maintenance/{train,test,RUL}_FD001.txt).

Honest caveat, stated plainly (same spirit as the Energy module's dataset
caveat): this is real, physically-measured aircraft turbofan engine sensor
data, run to actual failure — it is NOT facility HVAC/pump/chiller data.
There is no public, freely-licensed, sensor-level "run to failure" facility
equipment dataset of comparable quality and size available without a paid
Kaggle account. What C-MAPSS provides that's genuinely valuable here is the
thing that's hard to fake: real multivariate sensor degradation trajectories
that trend measurably as a machine approaches mechanical failure. That
degradation *pattern* (not the specific engine domain) is what a predictive-
maintenance ML model needs to learn from. So:
  - The underlying sensor VALUES and their degradation trends are 100% real
    measurements from real engines run to real failure.
  - The DOMAIN LABELS (asset names like "Chiller-04", sensor names like
    "vibration_index") are a relabeling onto a plausible facility fleet —
    same technique, same honesty bar, as Milestone 1's submeter-share
    derivation.
  - 8 of the 21 raw sensors are kept (the ones with real variance across
    the fleet — several C-MAPSS sensors are constant and carry no signal)
    and renamed to generic facility-equipment-sensor names.

Two outputs:
  1. maintenance_train_readings.csv — FULL run-to-failure trajectories
     (train_FD001, 100 units) — used ONLY to train the ML health/RUL model.
     Not loaded into the live app DB.
  2. maintenance_fleet_readings.csv — TRUNCATED mid-life trajectories
     (test_FD001, 100 units, each cut off before failure — true RUL is
     genuinely unknown from the sensor data alone) — this is the "current
     live fleet" the dashboard shows. RUL_FD001.txt (NASA's official
     ground-truth answer key for test_FD001) is kept SEPARATE and used only
     by the training script for held-out evaluation, never fed to the app.

Run:
    cd backend && python data/build_maintenance_dataset.py
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

RAW_DIR = Path(__file__).resolve().parent / "raw_maintenance"
OUT_DIR = Path(__file__).resolve().parent / "processed"
OUT_DIR.mkdir(exist_ok=True)

COLS = ["unit_nr", "cycle", "setting1", "setting2", "setting3"] + [f"s{i}" for i in range(1, 22)]

# Real sensor -> generic facility-sensor rename. Kept sensors are the ones
# with meaningful variance in FD001 (dropping near-constant s1,s5,s6,s10,
# s16,s18,s19 which the C-MAPSS literature consistently reports as
# uninformative for this sub-dataset).
SENSOR_RENAME = {
    "s2": "temp_stage1_c",
    "s3": "temp_stage2_c",
    "s4": "temp_stage3_c",
    "s7": "pressure_kpa",
    "s11": "vibration_index",
    "s12": "flow_rate",
    "s15": "efficiency_ratio",
    "s21": "bleed_load",
}

RUL_CLIP = 125  # standard C-MAPSS practice: RUL flattens out this far from failure

ASSET_CATALOG = [
    ("HVAC Chiller", "Mechanical Room A"),
    ("Air Handling Unit", "Roof Plant"),
    ("Water Pump", "Basement Utility"),
    ("Air Compressor", "Mechanical Room B"),
    ("Cooling Tower", "Roof Plant"),
    ("Boiler", "Basement Utility"),
    ("Elevator Motor", "Elevator Machine Room"),
    ("Backup Generator", "Generator Yard"),
]


def _read_raw(name: str) -> pd.DataFrame:
    return pd.read_csv(RAW_DIR / name, sep=r"\s+", header=None, names=COLS)


def _rename_sensors(df: pd.DataFrame) -> pd.DataFrame:
    keep = ["unit_nr", "cycle"] + list(SENSOR_RENAME.keys())
    out = df[keep].rename(columns=SENSOR_RENAME)
    return out


def build_train() -> pd.DataFrame:
    """Full run-to-failure trajectories, real RUL computed exactly (we have
    every cycle up to and including the failure cycle)."""
    df = _read_raw("train_FD001.txt")
    max_cycle = df.groupby("unit_nr")["cycle"].transform("max")
    df["true_rul_cycles"] = (max_cycle - df["cycle"]).clip(upper=RUL_CLIP)
    out = _rename_sensors(df)
    out["true_rul_cycles"] = df["true_rul_cycles"]
    out["asset_id"] = "AST-TRAIN-" + out["unit_nr"].astype(str).str.zfill(3)
    return out.drop(columns=["unit_nr"])


def build_fleet() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Truncated mid-life trajectories = the 'current' live fleet. True RUL
    is genuinely unknown from sensors alone (that's the ML task) — we do
    NOT attach RUL_FD001 ground truth here; it's reserved for held-out
    model evaluation in the training script only.

    Cycles are anchored onto real calendar dates, most recent cycle = today
    (same dynamic-anchoring approach as the Energy dataset), 1 cycle = 1
    operating day. Also returns an asset metadata frame (name/type/location).
    """
    df = _read_raw("test_FD001.txt")
    out = _rename_sensors(df)

    n_assets = df["unit_nr"].nunique()
    assets = []
    for i in range(1, n_assets + 1):
        asset_type, location = ASSET_CATALOG[(i - 1) % len(ASSET_CATALOG)]
        assets.append({
            "asset_id": f"AST-{i:03d}",
            "name": f"{asset_type.split()[0]}-{i:03d}",
            "asset_type": asset_type,
            "location": location,
            "building_id": "BLD-HQ-01",
        })
    assets_df = pd.DataFrame(assets)
    unit_to_asset = {i: f"AST-{i:03d}" for i in range(1, n_assets + 1)}
    out["asset_id"] = out["unit_nr"].map(unit_to_asset)

    # Anchor each asset's own cycle sequence so its LAST cycle = today,
    # 1 cycle = 1 operating day (matches the training data's cycle grain).
    today = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)
    out = out.sort_values(["asset_id", "cycle"]).reset_index(drop=True)
    max_cycle_per_asset = out.groupby("asset_id")["cycle"].transform("max")
    days_from_now = out["cycle"] - max_cycle_per_asset  # <= 0
    out["timestamp"] = out["asset_id"].map(lambda _: None)  # placeholder, set below
    out["timestamp"] = [today + timedelta(days=int(d)) for d in days_from_now]

    return out.drop(columns=["unit_nr"]), assets_df


if __name__ == "__main__":
    train_df = build_train()
    fleet_df, assets_df = build_fleet()

    train_path = OUT_DIR / "maintenance_train_readings.csv"
    fleet_path = OUT_DIR / "maintenance_fleet_readings.csv"
    assets_path = OUT_DIR / "maintenance_assets.csv"

    train_df.to_csv(train_path, index=False)
    fleet_df.to_csv(fleet_path, index=False)
    assets_df.to_csv(assets_path, index=False)

    print(f"train readings:  {len(train_df):>7} rows  ({train_df['asset_id'].nunique()} engines, full run-to-failure)  -> {train_path}")
    print(f"fleet readings:  {len(fleet_df):>7} rows  ({fleet_df['asset_id'].nunique()} assets, truncated/live)        -> {fleet_path}")
    print(f"fleet assets:    {len(assets_df):>7} rows                                                    -> {assets_path}")
