"""
Pure analytics functions over a readings DataFrame. Kept separate from the
agent so they're independently unit-testable and reusable by other agents
(e.g. a future Cost Agent can reuse consumption_summary()).
"""
import pandas as pd
import numpy as np

from app.core.config import settings


def consumption_summary(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"period": "n/a", "total_kwh": 0, "avg_hourly_kwh": 0,
                "peak_kwh": 0, "peak_timestamp": None,
                "min_kwh": 0, "min_timestamp": None}

    peak_row = df.loc[df["total_kwh"].idxmax()]
    min_row = df.loc[df["total_kwh"].idxmin()]
    return {
        "period": f"{df['timestamp'].min().date()} to {df['timestamp'].max().date()}",
        "total_kwh": round(df["total_kwh"].sum(), 2),
        "avg_hourly_kwh": round(df["total_kwh"].mean(), 2),
        "peak_kwh": round(peak_row["total_kwh"], 2),
        "peak_timestamp": peak_row["timestamp"],
        "min_kwh": round(min_row["total_kwh"], 2),
        "min_timestamp": min_row["timestamp"],
    }


def submeter_breakdown(df: pd.DataFrame) -> dict:
    if df.empty:
        return {k: 0 for k in [
            "hvac_kwh", "lighting_kwh", "plug_load_kwh", "other_kwh",
            "hvac_pct", "lighting_pct", "plug_load_pct", "other_pct"]}

    totals = {
        "hvac_kwh": df["hvac_kwh"].sum(),
        "lighting_kwh": df["lighting_kwh"].sum(),
        "plug_load_kwh": df["plug_load_kwh"].sum(),
        "other_kwh": df["other_kwh"].sum(),
    }
    grand_total = sum(totals.values()) or 1
    pct = {f"{k.replace('_kwh', '')}_pct": round(v / grand_total * 100, 1)
           for k, v in totals.items()}
    return {**{k: round(v, 2) for k, v in totals.items()}, **pct}


def trend_pct(df: pd.DataFrame) -> float:
    """Compare the most recent half of the window vs the prior half."""
    if len(df) < 4:
        return 0.0
    midpoint = len(df) // 2
    prev = df.iloc[:midpoint]["total_kwh"].mean()
    recent = df.iloc[midpoint:]["total_kwh"].mean()
    if prev == 0:
        return 0.0
    return round((recent - prev) / prev * 100, 1)


def detect_anomalies(df: pd.DataFrame) -> list[dict]:
    """
    Flag hours where consumption deviates sharply from the expected value
    for that hour-of-day (z-score against the hour-of-day's own mean/std,
    so a normal daytime peak isn't flagged just for being high).
    """
    if df.empty:
        return []

    work = df.copy()
    work["hour"] = work["timestamp"].dt.hour
    hourly_stats = work.groupby("hour")["total_kwh"].agg(["mean", "std"]).fillna(0)

    anomalies = []
    for _, row in work.iterrows():
        stats = hourly_stats.loc[row["hour"]]
        std = stats["std"] if stats["std"] > 0 else 1e-6
        z = (row["total_kwh"] - stats["mean"]) / std
        if abs(z) >= settings.ANOMALY_ZSCORE_THRESHOLD:
            severity = "high" if abs(z) >= settings.ANOMALY_ZSCORE_THRESHOLD * 1.4 else "medium"
            anomalies.append({
                "timestamp": row["timestamp"],
                "total_kwh": round(row["total_kwh"], 2),
                "expected_kwh": round(stats["mean"], 2),
                "z_score": round(float(z), 2),
                "severity": severity,
            })
    anomalies.sort(key=lambda a: abs(a["z_score"]), reverse=True)
    return anomalies


def off_hours_baseline_waste(df: pd.DataFrame) -> dict:
    """
    Compares average off-hours load (e.g. 8PM-6AM, when a facility should
    be mostly idle) against daytime average. A high ratio suggests phantom
    loads: equipment left running, HVAC not set back, lighting not zoned.
    """
    if df.empty:
        return {"off_hours_avg": 0, "daytime_avg": 0, "waste_ratio_pct": 0}

    work = df.copy()
    work["hour"] = work["timestamp"].dt.hour
    off_mask = (work["hour"] >= settings.OFF_HOURS_START) | (work["hour"] < settings.OFF_HOURS_END)

    off_hours_avg = work.loc[off_mask, "total_kwh"].mean() or 0
    daytime_avg = work.loc[~off_mask, "total_kwh"].mean() or 1e-6
    ratio = round(off_hours_avg / daytime_avg * 100, 1)

    return {
        "off_hours_avg": round(off_hours_avg, 2),
        "daytime_avg": round(daytime_avg, 2),
        "waste_ratio_pct": ratio,  # off-hours load as % of daytime load
    }


def temperature_correlation(df: pd.DataFrame) -> dict:
    """
    Weather-normalized view: correlates consumption with outdoor temperature
    to separate weather-driven load (HVAC responding to hot/cold days) from
    non-weather-driven load (baseline that shouldn't move with temperature).
    """
    if df.empty or "outdoor_temp_c" not in df.columns or df["outdoor_temp_c"].isna().all():
        return {"available": False}

    clean = df.dropna(subset=["outdoor_temp_c"])
    corr = clean["total_kwh"].corr(clean["outdoor_temp_c"])

    # Split into cold/mild/hot terciles to show load response
    clean = clean.copy()
    clean["temp_band"] = pd.qcut(clean["outdoor_temp_c"], 3, labels=["cold", "mild", "hot"], duplicates="drop")
    band_avg = clean.groupby("temp_band", observed=True)["total_kwh"].mean().round(2).to_dict()

    return {
        "available": True,
        "correlation": round(float(corr), 2) if pd.notna(corr) else 0.0,
        "avg_load_by_temp_band": {str(k): v for k, v in band_avg.items()},
    }


def occupancy_correlation(df: pd.DataFrame) -> dict:
    """
    Correlates consumption with occupancy headcount. Low correlation (or
    high consumption at near-zero occupancy) signals load that isn't
    actually tied to people being present — a strong efficiency signal.
    """
    if df.empty or "occupancy_count" not in df.columns or df["occupancy_count"].isna().all():
        return {"available": False}

    clean = df.dropna(subset=["occupancy_count"])
    corr = clean["total_kwh"].corr(clean["occupancy_count"])

    unoccupied = clean[clean["occupancy_count"] == 0]
    occupied = clean[clean["occupancy_count"] > 0]
    unoccupied_avg = round(unoccupied["total_kwh"].mean(), 2) if len(unoccupied) else 0
    occupied_avg = round(occupied["total_kwh"].mean(), 2) if len(occupied) else 0
    unoccupied_pct_of_occupied = round(unoccupied_avg / occupied_avg * 100, 1) if occupied_avg else 0

    return {
        "available": True,
        "correlation": round(float(corr), 2) if pd.notna(corr) else 0.0,
        "avg_load_when_unoccupied_kwh": unoccupied_avg,
        "avg_load_when_occupied_kwh": occupied_avg,
        "unoccupied_load_pct_of_occupied": unoccupied_pct_of_occupied,
    }
