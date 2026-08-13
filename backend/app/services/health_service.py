"""
Loads the trained equipment health / RUL model
(ml_models/maintenance/train_health_model.py) and serves live predictions
for the current fleet. Mirrors forecast_service.py's pattern in the Energy
module: the model file + honest metrics are read once and cached, and every
prediction carries a confidence signal derived from the model's own
held-out accuracy rather than presenting every prediction as equally
trustworthy.
"""
import json
from datetime import timedelta
from pathlib import Path
import joblib
import pandas as pd

MODEL_DIR = Path(__file__).resolve().parents[2] / "ml_models" / "maintenance"
MODEL_PATH = MODEL_DIR / "health_rul_model.pkl"
METRICS_PATH = MODEL_DIR / "model_metrics.json"
SCATTER_PATH = MODEL_DIR / "prediction_scatter.json"

ROLLING_COLS = ["efficiency_ratio", "vibration_index"]


def get_prediction_scatter() -> dict:
    """Actual-vs-predicted RUL for the winning model, on all 100 NASA
    held-out test engines — same reliability diagnostic as the Energy
    forecast scatter."""
    if not SCATTER_PATH.exists():
        raise FileNotFoundError(
            f"No prediction scatter data at {SCATTER_PATH}. "
            "Run: python ml_models/maintenance/train_health_model.py"
        )
    return json.loads(SCATTER_PATH.read_text())

# Health-score status buckets (0-100 scale, derived from predicted RUL).
STATUS_THRESHOLDS = [
    (75, "Excellent"),
    (50, "Good"),
    (25, "Warning"),
    (0, "Critical"),
]

_cache = {}


def is_model_available() -> bool:
    return MODEL_PATH.exists()


def _load_model():
    if "model" not in _cache:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"No trained health model at {MODEL_PATH}. "
                "Run: python ml_models/maintenance/train_health_model.py"
            )
        _cache["model"] = joblib.load(MODEL_PATH)
    return _cache["model"]


def get_confidence() -> dict:
    if not METRICS_PATH.exists():
        return {"available": False}
    metrics = json.loads(METRICS_PATH.read_text())
    improvement = metrics["improvement_over_naive_pct"]
    if improvement >= 40:
        confidence = "high"
    elif improvement >= 15:
        confidence = "medium"
    else:
        confidence = "low"
    best = metrics["all_models"][metrics["best_model"]]
    return {
        "available": True,
        "model_used": metrics["best_model"],
        "mae_cycles": best["held_out_test_mae_cycles"],
        "r2": best["held_out_test_r2"],
        "improvement_over_naive_pct": improvement,
        "confidence": confidence,
    }


def rul_to_health_score(rul_cycles: float, clip: int = 125) -> float:
    return round(max(0.0, min(100.0, (rul_cycles / clip) * 100)), 1)


def health_score_to_status(health_score: float) -> str:
    for threshold, label in STATUS_THRESHOLDS:
        if health_score >= threshold:
            return label
    return "Critical"


def _build_features(asset_df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    """asset_df = full reading history for ONE asset, sorted by cycle.
    Recomputes the same rolling features used at training time from that
    asset's own trailing 5-cycle window, then returns just the latest row."""
    df = asset_df.sort_values("cycle").reset_index(drop=True).copy()
    for col in ROLLING_COLS:
        df[f"{col}_roll_mean5"] = df[col].rolling(5, min_periods=1).mean()
        df[f"{col}_roll_std5"] = df[col].rolling(5, min_periods=1).std().fillna(0)
    latest = df.iloc[[-1]]
    return latest[feature_cols]


def predict_asset_health(asset_df: pd.DataFrame) -> dict:
    """asset_df: reading history for one asset (>=1 row), ordered or not
    (sorted internally). Returns predicted RUL, health score, status,
    predicted maintenance date, and model confidence."""
    bundle = _load_model()
    model, features, clip = bundle["model"], bundle["features"], bundle["rul_clip"]

    X = _build_features(asset_df, features)
    predicted_rul = float(model.predict(X)[0])
    predicted_rul = max(0.0, predicted_rul)
    health_score = rul_to_health_score(predicted_rul, clip)
    status = health_score_to_status(health_score)

    latest_row = asset_df.sort_values("cycle").iloc[-1]
    latest_timestamp = pd.to_datetime(latest_row["timestamp"])
    predicted_maintenance_date = latest_timestamp + timedelta(days=round(predicted_rul))

    return {
        "predicted_rul_cycles": round(predicted_rul, 1),
        "health_score": health_score,
        "status": status,
        "latest_cycle": int(latest_row["cycle"]),
        "latest_timestamp": latest_timestamp,
        "predicted_maintenance_date": predicted_maintenance_date,
        "confidence": get_confidence(),
    }
