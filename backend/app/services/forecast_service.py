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
import pandas as pd

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


def forecast(df: pd.DataFrame, horizon: str = "1h") -> dict:
    """Predicts total_kwh `horizon` ahead using the model trained for that
    specific horizon."""
    if horizon not in VALID_HORIZONS:
        raise ValueError(f"horizon must be one of {VALID_HORIZONS}, got '{horizon}'")

    bundle = _load_model(horizon)
    model, features, horizon_steps = bundle["model"], bundle["features"], bundle["horizon_steps"]

    required_history = max(16, 24 * 4) + 1  # 4h rolling window + 24h-ago lookup
    if len(df) < required_history:
        raise ValueError(f"Need at least {required_history} readings of history to forecast")

    work = df.sort_values("timestamp").reset_index(drop=True).copy()
    work["timestamp"] = pd.to_datetime(work["timestamp"])

    latest = work.iloc[-1]
    trailing_4h = work.tail(16)
    yesterday_same_time = work.iloc[-1 - 24 * 4] if len(work) > 24 * 4 else latest

    row = {
        "hour": latest["timestamp"].hour,
        "day_of_week": latest["timestamp"].dayofweek,
        "is_weekend": int(latest["timestamp"].dayofweek >= 5),
        "month": latest["timestamp"].month,
        "outdoor_temp_c": latest.get("outdoor_temp_c", trailing_4h["outdoor_temp_c"].mean()),
        "occupancy_count": latest.get("occupancy_count", trailing_4h["occupancy_count"].mean()),
        "kwh_now": latest["total_kwh"],
        "kwh_rolling_mean_4h": trailing_4h["total_kwh"].mean(),
        "kwh_rolling_std_4h": trailing_4h["total_kwh"].std(),
        "kwh_same_hour_yesterday": yesterday_same_time["total_kwh"],
    }
    X = pd.DataFrame([row])[features]
    prediction = float(model.predict(X)[0])

    forecast_time = latest["timestamp"] + pd.Timedelta(minutes=15 * horizon_steps)
    confidence = get_horizon_confidence(horizon)

    return {
        "horizon": horizon,
        "current_kwh": round(float(latest["total_kwh"]), 2),
        "current_timestamp": latest["timestamp"],
        "predicted_kwh": round(prediction, 2),
        "predicted_timestamp": forecast_time,
        "model_used": bundle["model_name"],
        "confidence": confidence,
    }


# Backward-compatible alias used by earlier code/tests
def forecast_next_hour(df: pd.DataFrame) -> dict:
    return forecast(df, horizon="1h")
