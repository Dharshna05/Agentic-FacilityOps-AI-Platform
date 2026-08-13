"""
Final Milestone 1+ dataset builder.

Produces backend/data/raw/energy_readings_raw.csv — the single feed the
ingestion pipeline (data_service.ingest_from_csv) consumes.

Combines THREE real, public datasets onto one 15-minute timeline:
  - Power Consumption  <- PJM Interconnection hourly grid load (real, 2002-2018)
  - Outdoor Temperature <- Environment Canada hourly weather (real, 2012)
  - Occupancy           <- UCI Occupancy Detection dataset (Candanedo, 2016),
                            real minute-level office sensor data

Each source's real shape/cycles/noise is preserved; they're stitched onto a
shared timeline since the three don't share an actual overlapping recording
period (documented in README.md). The power signal is then split into
HVAC/Lighting/Plug-load/Other submeters using standard commercial building
load-share ratios.

IMPORTANT: the timeline is anchored to END dynamically at "today" (the date
this script is run), not a fixed past date — so the dataset always reads as
current/recent rather than visibly stale. Re-run this script periodically
(or on deploy) to keep the data looking live. This is a labeling choice, not
a claim that the underlying source recordings themselves are from today —
that provenance is documented in README.md and stays accurate regardless of
what date range the labels are shifted to.
"""
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

np.random.seed(7)

RAW_DIR = Path(__file__).resolve().parent / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent / "processed"

N_DAYS = 365          # a full year of data (was 210) — more data, per request
FREQ = "15min"
PERIODS = N_DAYS * 24 * 4

# End "today" (rounded to the start of the current hour) and go back N_DAYS —
# always current no matter when this script is re-run.
end_anchor = pd.Timestamp(datetime.now()).floor("h")
start_anchor = end_anchor - timedelta(days=N_DAYS) + timedelta(minutes=15)
target_index = pd.date_range(start_anchor, end_anchor, freq=FREQ)
PERIODS = len(target_index)

# ---------- 1. Power Consumption (real PJM grid load, rescaled) ----------
pjm = pd.read_csv(RAW_DIR / "PJME_hourly_full.csv", parse_dates=["Datetime"]).sort_values("Datetime")
hours_needed = N_DAYS * 24 + 24
window = pjm.tail(hours_needed).reset_index(drop=True)
mw = window["PJME_MW"].values
scaled = (mw - mw.min()) / (mw.max() - mw.min())
power_hourly = 150 + scaled * 350  # facility kW band

power_series = pd.Series(power_hourly, index=pd.date_range(target_index[0], periods=len(power_hourly), freq="h"))
power_15min = power_series.resample(FREQ).interpolate("linear").reindex(target_index).ffill().bfill()

# ---------- 2. Outdoor Temperature (real Environment Canada 2012, full year) ----------
weather = pd.read_csv(RAW_DIR / "weather_2012_raw.csv")
weather.columns = [c.strip() for c in weather.columns]
weather["Date/Time"] = pd.to_datetime(weather["Date/Time"])
temp_hourly = weather.set_index("Date/Time")["Temp (C)"]
# Full year (8784 rows) tiled/truncated to match however many hours we need,
# preserving real seasonal shape (Jan cold -> Jul warm -> Dec cold again).
hours_needed_temp = N_DAYS * 24 + 24
reps = (hours_needed_temp // len(temp_hourly)) + 1
temp_tiled = pd.concat([temp_hourly] * reps).iloc[:hours_needed_temp]
temp_series = pd.Series(temp_tiled.values, index=pd.date_range(target_index[0], periods=len(temp_tiled), freq="h"))
temp_15min = temp_series.resample(FREQ).interpolate("linear").reindex(target_index).ffill().bfill()

# ---------- 3. Occupancy (real UCI Occupancy Detection pattern) ----------
occ_frames = [pd.read_csv(RAW_DIR / f"occ_{f}") for f in ("datatraining.csv", "datatest.csv", "datatest2.csv")]
occ = pd.concat(occ_frames, ignore_index=True)
occ["minute_of_day"] = (occ["NSM"] // 60).astype(int)
occ["bin_of_day"] = occ["minute_of_day"] // 15
profile = occ.groupby(["WeekStatus", "bin_of_day"])["Occupancy"].mean().to_dict()

target_df = pd.DataFrame(index=target_index)
target_df["dow"] = target_df.index.dayofweek
target_df["is_weekday"] = (target_df["dow"] < 5).astype(int)
target_df["bin_of_day"] = (target_df.index.hour * 60 + target_df.index.minute) // 15
target_df["occ_fraction"] = target_df.apply(
    lambda r: profile.get((r["is_weekday"], r["bin_of_day"]), 0.0), axis=1
)

max_capacity = 8
noise = np.random.normal(0, 0.4, len(target_df))
headcount = (target_df["occ_fraction"] * max_capacity + noise).clip(lower=0).round().astype(int)

# ---------- 4. Submeter split ----------
def split(series, share, noise_std=0.03):
    noise_factor = 1 + np.random.normal(0, noise_std, len(series))
    return (series * share * noise_factor).round(2)

total_kwh = power_15min.values
hvac_kwh = split(total_kwh, 0.40)
lighting_kwh = split(total_kwh, 0.20)
plug_load_kwh = split(total_kwh, 0.25)
other_kwh = split(total_kwh, 0.15)

final = pd.DataFrame({
    "building_id": "BLD-HQ-01",
    "sensor_id": "MAIN-METER-01",
    "timestamp": target_index,
    "total_kwh": total_kwh.round(2),
    "hvac_kwh": hvac_kwh,
    "lighting_kwh": lighting_kwh,
    "plug_load_kwh": plug_load_kwh,
    "other_kwh": other_kwh,
    "outdoor_temp_c": temp_15min.values.round(2),
    "occupancy_count": headcount.values,
})

PROCESSED_DIR.mkdir(exist_ok=True)
final.to_csv(PROCESSED_DIR / "energy_readings.csv", index=False)
final.to_csv(RAW_DIR / "energy_readings_raw.csv", index=False)

print(f"Rows: {len(final)}")
print(f"Date range: {final['timestamp'].min()} to {final['timestamp'].max()}")
print(final.head())
print(f"\nOccupancy range: {final['occupancy_count'].min()}-{final['occupancy_count'].max()}")
print(f"Power range: {final['total_kwh'].min()}-{final['total_kwh'].max()} kW")
print(f"Temp range: {final['outdoor_temp_c'].min()}-{final['outdoor_temp_c'].max()} C")
