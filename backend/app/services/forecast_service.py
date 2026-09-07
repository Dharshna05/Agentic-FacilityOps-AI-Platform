"""
Loads trained forecasting models (ml_models/energy/train_forecast_model.py)
and serves multi-horizon energy consumption predictions from live data.

Three horizons are available (1h, 6h, 24h), each with its OWN trained
model — see train_forecast_model.py for why. Their real accuracy differs
significantly (1h and 6h are strong; 24h is only marginally better than a
naive baseline) — this is reported honestly via model_metrics.json rather
than hidden, so the API/UI can show a confidence signal per horizon
instead of implying uniform accuracy across all of them.
"""
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from app.utils.drift_detection import compute_drift

MODEL_DIR = Path(__file__).resolve().parents[2] / "ml_models" / "energy"
METRICS_PATH = MODEL_DIR / "model_metrics.json"
SCATTER_PATH = MODEL_DIR / "prediction_scatter.json"

VALID_HORIZONS = ("1h", "6h", "24h")

_cache = {}


def get_prediction_scatter(horizon: str) -> dict:
    """Actual-vs-predicted points for the winning model at this horizon, on
    held-out test data — the reliability diagnostic: points hugging the
    y=x diagonal mean accurate predictions, a scattered cloud means the
    model shouldn't be trusted at this horizon (see the 24h model, which
    is honestly only ~5% better than naive)."""
    if not SCATTER_PATH.exists():
        raise FileNotFoundError(
            f"No prediction scatter data at {SCATTER_PATH}. "
            "Run: python ml_models/energy/train_forecast_model.py"
        )
    all_scatter = json.loads(SCATTER_PATH.read_text())
    if horizon not in all_scatter:
        raise ValueError(f"No scatter data for horizon '{horizon}'")
    return all_scatter[horizon]


def _model_path(horizon: str) -> Path:
    return MODEL_DIR / f"consumption_forecast_model_{horizon}.pkl"


def _load_model(horizon: str):
    if horizon not in _cache:
        path = _model_path(horizon)
        if not path.exists():
            raise FileNotFoundError(
                f"No trained model for horizon '{horizon}' at {path}. "
                "Run: python ml_models/energy/train_forecast_model.py"
            )
        _cache[horizon] = joblib.load(path)
    return _cache[horizon]


def is_model_available(horizon: str = "1h") -> bool:
    return _model_path(horizon).exists()


def get_horizon_confidence(horizon: str) -> dict:
    """Reports the model's own honest accuracy for this horizon (from
    training-time evaluation) so callers can show a confidence signal
    instead of presenting every horizon as equally trustworthy."""
    if not METRICS_PATH.exists():
        return {"available": False}
    metrics = json.loads(METRICS_PATH.read_text())
    horizon_data = metrics.get("horizons", {}).get(horizon)
    if not horizon_data:
        return {"available": False}
    best = horizon_data["all_models"][horizon_data["best_model"]]
    improvement = horizon_data["improvement_over_best_naive_pct"]
    if improvement >= 40:
        confidence = "high"
    elif improvement >= 15:
        confidence = "medium"
    else:
        confidence = "low"
    return {
        "available": True,
        "model_used": horizon_data["best_model"],
        "mae_kwh": best["held_out_test_mae_kwh"],
        "r2": best["held_out_test_r2"],
        "improvement_over_naive_pct": improvement,
        "confidence": confidence,
    }


def get_model_comparison(horizon: str) -> dict:
    """All 3 candidate models' honest held-out metrics for this horizon,
    not just the winner — surfaces the same multi-model comparison that
    training already does (linear_regression / random_forest /
    gradient_boosting) so the dashboard can show it, not just silently
    pick a winner behind the scenes."""
    if not METRICS_PATH.exists():
        return {"available": False}
    metrics = json.loads(METRICS_PATH.read_text())
    horizon_data = metrics.get("horizons", {}).get(horizon)
    if not horizon_data:
        return {"available": False}
    return {
        "available": True,
        "horizon": horizon,
        "best_model": horizon_data["best_model"],
        "models": horizon_data["all_models"],
        "naive_flat_mae_kwh": horizon_data["naive_flat_mae_kwh"],
        "naive_daily_mae_kwh": horizon_data["naive_daily_mae_kwh"],
    }


def get_data_drift(df: pd.DataFrame) -> dict:
    """Compares the CURRENT data (bundled dataset, or an uploaded test
    CSV) against the distribution the model was originally TRAINED on —
    see app/utils/drift_detection.py for what this proxy does and doesn't
    tell you."""
    if not METRICS_PATH.exists():
        return {"available": False}
    metrics = json.loads(METRICS_PATH.read_text())
    training_dist = metrics.get("training_distribution")
    if not training_dist:
        return {"available": False}

    current_means = {
        col: float(df[col].mean()) if col in df.columns and not df[col].dropna().empty else None
        for col in training_dist
    }
    return compute_drift(current_means, training_dist)


def forecast(df: pd.DataFrame, horizon: str = "1h") -> dict:
    """Predicts total_kwh `horizon` ahead using the model trained for that
    specific horizon."""
    if horizon not in VALID_HORIZONS:
        raise ValueError(f"horizon must be one of {VALID_HORIZONS}, got '{horizon}'")

    bundle = _load_model(horizon)
    model, features, horizon_steps = bundle["model"], bundle["features"], bundle["horizon_steps"]

    # 24h window is nice-to-have (falls back to whatever history exists);
    # the 7-day-ago weekly lookup is likewise best-effort. Only the 4h
    # rolling window is strictly required to produce a prediction at all.
    required_history = 16 + 1  # 4h rolling window, minimum
    if len(df) < required_history:
        raise ValueError(f"Need at least {required_history} readings of history to forecast")

    work = df.sort_values("timestamp").reset_index(drop=True).copy()
    work["timestamp"] = pd.to_datetime(work["timestamp"])

    latest = work.iloc[-1]
    trailing_4h = work.tail(16)
    trailing_24h = work.tail(96) if len(work) >= 96 else work
    yesterday_same_time = work.iloc[-1 - 24 * 4] if len(work) > 24 * 4 else latest
    last_week_same_time = work.iloc[-1 - 7 * 24 * 4] if len(work) > 7 * 24 * 4 else yesterday_same_time

    hour = latest["timestamp"].hour
    dow = latest["timestamp"].dayofweek
    kwh_now = latest["total_kwh"]
    kwh_roll_mean_4h = trailing_4h["total_kwh"].mean()

    def _component(col):
        # Component breakdown columns (hvac/lighting/plug/other) may be
        # absent from a caller's DataFrame in some call sites — fall back
        # to 0 rather than raising, since these are secondary signals.
        return float(latest[col]) if col in work.columns else 0.0

    row = {
        "hour": hour,
        "day_of_week": dow,
        "is_weekend": int(dow >= 5),
        "month": latest["timestamp"].month,
        "hour_sin": np.sin(2 * np.pi * hour / 24),
        "hour_cos": np.cos(2 * np.pi * hour / 24),
        "dow_sin": np.sin(2 * np.pi * dow / 7),
        "dow_cos": np.cos(2 * np.pi * dow / 7),
        "outdoor_temp_c": latest.get("outdoor_temp_c", trailing_4h["outdoor_temp_c"].mean()),
        "occupancy_count": latest.get("occupancy_count", trailing_4h["occupancy_count"].mean()),
        "kwh_now": kwh_now,
        "kwh_rolling_mean_4h": kwh_roll_mean_4h,
        "kwh_rolling_std_4h": trailing_4h["total_kwh"].std(),
        "kwh_rolling_mean_24h": trailing_24h["total_kwh"].mean(),
        "kwh_rolling_std_24h": trailing_24h["total_kwh"].std(),
        "kwh_momentum_4h": kwh_now - kwh_roll_mean_4h,
        "kwh_same_hour_yesterday": yesterday_same_time["total_kwh"],
        "kwh_same_hour_last_week": last_week_same_time["total_kwh"],
        "hvac_kwh_now": _component("hvac_kwh"),
        "lighting_kwh_now": _component("lighting_kwh"),
        "plug_load_kwh_now": _component("plug_load_kwh"),
        "other_kwh_now": _component("other_kwh"),
    }
    X = pd.DataFrame([row])[features].fillna(0)
    prediction = float(model.predict(X)[0])

    forecast_time = latest["timestamp"] + pd.Timedelta(minutes=15 * horizon_steps)
    confidence = get_horizon_confidence(horizon)
    data_drift = get_data_drift(work)

    return {
        "horizon": horizon,
        "current_kwh": round(float(latest["total_kwh"]), 2),
        "current_timestamp": latest["timestamp"],
        "predicted_kwh": round(prediction, 2),
        "predicted_timestamp": forecast_time,
        "model_used": bundle["model_name"],
        "confidence": confidence,
        "data_drift": data_drift,
    }


# Backward-compatible alias used by earlier code/tests
def forecast_next_hour(df: pd.DataFrame) -> dict:
    return forecast(df, horizon="1h")
