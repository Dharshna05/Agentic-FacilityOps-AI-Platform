"""
Analytics for the Maintenance module — mirrors the shape of
energy_analytics.py: pure functions that take DataFrames and return plain
dicts/lists, called by MaintenanceAgent.analyze().
"""
import numpy as np
import pandas as pd

from app.services import health_service


def score_asset(asset_meta: dict, readings_df: pd.DataFrame) -> dict:
    """Runs the ML model for one asset and attaches its metadata + a
    short-window degradation trend on the sensor the model weighs most
    heavily (vibration_index — see model_metrics.json feature importances)."""
    prediction = health_service.predict_asset_health(readings_df)
    trend = degradation_trend(readings_df)
    return {
        "asset_id": asset_meta["asset_id"],
        "name": asset_meta["name"],
        "asset_type": asset_meta["asset_type"],
        "location": asset_meta["location"],
        **prediction,
        "trend": trend,
    }


def degradation_trend(readings_df: pd.DataFrame, window: int = 10) -> dict:
    """Slope of vibration_index over the trailing `window` cycles — a
    simple, explainable signal of whether an asset's key wear indicator is
    actively worsening right now, independent of the ML model's longer-
    horizon RUL estimate."""
    df = readings_df.sort_values("cycle").tail(window)
    if len(df) < 3:
        return {"available": False}
    x = np.arange(len(df))
    y = df["vibration_index"].values
    slope = float(np.polyfit(x, y, 1)[0])
    direction = "worsening" if slope > 0.002 else "stable" if abs(slope) <= 0.002 else "improving"
    return {"available": True, "vibration_slope_per_cycle": round(slope, 5), "direction": direction}


def fleet_summary(scored_assets: list[dict]) -> dict:
    if not scored_assets:
        return {
            "assets_monitored": 0, "avg_health_score": 0, "status_counts": {},
            "status_pct": {}, "open_critical": 0,
        }
    n = len(scored_assets)
    statuses = [a["status"] for a in scored_assets]
    counts = {label: statuses.count(label) for _, label in health_service.STATUS_THRESHOLDS}
    pct = {k: round(v / n * 100, 1) for k, v in counts.items()}
    avg_health = round(sum(a["health_score"] for a in scored_assets) / n, 1)
    return {
        "assets_monitored": n,
        "avg_health_score": avg_health,
        "status_counts": counts,
        "status_pct": pct,
        "open_critical": counts.get("Critical", 0),
    }


def risk_ranking(scored_assets: list[dict], limit: int = 10) -> list[dict]:
    """Most at-risk first (lowest health score)."""
    return sorted(scored_assets, key=lambda a: a["health_score"])[:limit]
