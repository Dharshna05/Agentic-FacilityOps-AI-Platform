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
import numpy as np
import pandas as pd

from app.utils.rul_features import add_engineered_features, top_contributing_factors, SENSOR_COLS
from app.utils.drift_detection import compute_drift

MODEL_DIR = Path(__file__).resolve().parents[2] / "ml_models" / "maintenance"
MODEL_PATH = MODEL_DIR / "health_rul_model.pkl"
LSTM_MODEL_PATH = MODEL_DIR / "health_rul_lstm.keras"
LSTM_SCALER_PATH = MODEL_DIR / "health_rul_lstm_scaler.pkl"
METRICS_PATH = MODEL_DIR / "model_metrics.json"
SCATTER_PATH = MODEL_DIR / "prediction_scatter.json"
LSTM_SEQUENCE_LENGTH = 40


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


def _get_live_model_name() -> str:
    """Which model actually makes the point RUL prediction. Defaults to
    the tree ensemble if model_metrics.json has no `live_model` key yet
    (e.g. an older training run, or the LSTM script hasn't been run) —
    old behavior is preserved rather than silently requiring a retrain."""
    if not METRICS_PATH.exists():
        return "ensemble_blend"
    metrics = json.loads(METRICS_PATH.read_text())
    return metrics.get("live_model") or metrics.get("best_model", "ensemble_blend")


def is_lstm_live() -> bool:
    return _get_live_model_name() == "lstm_deep_learning" and LSTM_MODEL_PATH.exists() and LSTM_SCALER_PATH.exists()


def _load_lstm():
    """Cached (model, scaler) pair for the deep-learning RUL model — only
    imported/loaded if it's actually the live model, so a deployment that
    never ran train_lstm_rul_model.py doesn't pay TensorFlow's import cost
    or need the .keras file to exist."""
    if "lstm_model" not in _cache:
        import tensorflow as tf
        _cache["lstm_model"] = tf.keras.models.load_model(LSTM_MODEL_PATH)
        _cache["lstm_scaler"] = joblib.load(LSTM_SCALER_PATH)
    return _cache["lstm_model"], _cache["lstm_scaler"]


def _build_lstm_sequence(asset_df: pd.DataFrame) -> np.ndarray:
    """The asset's last LSTM_SEQUENCE_LENGTH cycles of RAW sensor readings
    (not engineered features — the LSTM learns its own temporal pattern
    from the raw trajectory). Front-pads by repeating the earliest
    available reading if the asset has fewer than LSTM_SEQUENCE_LENGTH
    readings so far — same padding convention train_lstm_rul_model.py uses
    for NASA's own truncated test engines, so live inference on a
    brand-new/short-lived asset behaves the same way the held-out
    evaluation did, not some untested ad-hoc fallback."""
    ordered = asset_df.sort_values("cycle")
    values = ordered[SENSOR_COLS].values
    if len(values) >= LSTM_SEQUENCE_LENGTH:
        return values[-LSTM_SEQUENCE_LENGTH:]
    pad = np.repeat(values[:1], LSTM_SEQUENCE_LENGTH - len(values), axis=0)
    return np.vstack([pad, values])


def _load_model():
    if "model" not in _cache:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"No trained health model at {MODEL_PATH}. "
                "Run: python ml_models/maintenance/train_health_model.py"
            )
        _cache["model"] = joblib.load(MODEL_PATH)
    return _cache["model"]


def get_data_drift(asset_df: pd.DataFrame) -> dict:
    """Does THIS asset's current sensor readings still look like what the
    RUL model (tree-based or LSTM, whichever is live) was trained on —
    see app/utils/drift_detection.py. Checked per-asset (not fleet-wide)
    since a single mislabeled/wrong-unit sensor reading on one asset is
    exactly the kind of thing this should catch, and averaging across the
    whole fleet first would dilute it away."""
    if not METRICS_PATH.exists():
        return {"available": False}
    metrics = json.loads(METRICS_PATH.read_text())
    training_dist = metrics.get("training_distribution")
    if not training_dist:
        return {"available": False}
    current_means = {
        col: float(asset_df[col].mean()) if col in asset_df.columns and not asset_df[col].dropna().empty else None
        for col in training_dist
    }
    return compute_drift(current_means, training_dist)


def get_confidence() -> dict:
    if not METRICS_PATH.exists():
        return {"available": False}
    metrics = json.loads(METRICS_PATH.read_text())
    live_model = _get_live_model_name()
    model_data = metrics["all_models"].get(live_model, metrics["all_models"][metrics["best_model"]])

    # improvement_over_naive_pct in the file was computed against the
    # ORIGINAL (tree-model) comparison set — recompute it honestly for
    # whichever model is actually live, using that model's own MAE against
    # the same naive baseline, rather than reusing a number that may not
    # belong to this model.
    naive_mae = metrics["naive_baseline"]["mae_cycles"] if isinstance(metrics.get("naive_baseline"), dict) else metrics.get("naive_baseline")
    model_mae = model_data["held_out_test_mae_cycles"]
    improvement = round((1 - model_mae / naive_mae) * 100, 1) if naive_mae else metrics.get("improvement_over_naive_pct", 0)

    if improvement >= 40:
        confidence = "high"
    elif improvement >= 15:
        confidence = "medium"
    else:
        confidence = "low"
    return {
        "available": True,
        "model_used": live_model,
        "is_deep_learning": live_model == "lstm_deep_learning",
        "mae_cycles": model_data["held_out_test_mae_cycles"],
        "r2": model_data["held_out_test_r2"],
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
    """asset_df = full reading history for ONE asset. Recomputes the exact
    same engineered features used at training time (shared with
    train_health_model.py via app.utils.rul_features, so the two paths
    can never silently drift apart), then returns just the latest row."""
    df = asset_df.copy()
    df["asset_id"] = "current"  # single-asset frame; group key is a no-op here
    df = add_engineered_features(df, "asset_id")
    latest = df.sort_values("cycle").iloc[[-1]]
    return latest[feature_cols]


def predict_asset_health(asset_df: pd.DataFrame) -> dict:
    """asset_df: reading history for one asset (>=1 row), ordered or not
    (sorted internally). Returns predicted RUL — with an honest 80%
    prediction interval, not just a point estimate — health score, status,
    predicted maintenance date, and model confidence.

    Point prediction: uses the LSTM deep-learning model if it's the live
    model (model_metrics.json's `live_model`, set by whichever training
    script ran last and won honestly — see train_lstm_rul_model.py),
    otherwise the tree-based ensemble — same function signature and return
    shape either way, so callers/routes/frontend don't need to know or
    care which model is actually live.

    Prediction interval + explainability: ALWAYS computed from the
    tree-based quantile models and feature importances, even when the
    LSTM makes the point prediction. This is a deliberate choice, not an
    oversight — training a matching quantile-regression LSTM pair was out
    of scope for this pass, and the tree model's per-feature explanation
    ("driven mainly by rising vibration_index") is still genuinely
    informative context for a maintenance technician regardless of which
    model produced the headline number.
    """
    bundle = _load_model()
    tree_model, features, clip = bundle["model"], bundle["features"], bundle["rul_clip"]
    lo_model, hi_model = bundle.get("lo_model"), bundle.get("hi_model")

    X = _build_features(asset_df, features)

    if is_lstm_live():
        lstm_model, scaler = _load_lstm()
        seq = _build_lstm_sequence(asset_df)
        seq_scaled = scaler.transform(seq).reshape(1, LSTM_SEQUENCE_LENGTH, len(SENSOR_COLS))
        predicted_rul = max(0.0, min(float(lstm_model.predict(seq_scaled, verbose=0)[0][0]), clip))
    else:
        predicted_rul = max(0.0, min(float(tree_model.predict(X)[0]), clip))

    health_score = rul_to_health_score(predicted_rul, clip)
    status = health_score_to_status(health_score)

    rul_lower = rul_upper = None
    if lo_model is not None and hi_model is not None:
        lo = max(0.0, min(float(lo_model.predict(X)[0]), clip))
        hi = max(0.0, min(float(hi_model.predict(X)[0]), clip))
        rul_lower, rul_upper = round(min(lo, hi), 1), round(max(lo, hi), 1)

    factors = top_contributing_factors(
        X.iloc[0].to_dict(),
        bundle.get("feature_means", {}),
        bundle.get("feature_stds", {}),
        bundle.get("feature_importances") or {},
    )

    latest_row = asset_df.sort_values("cycle").iloc[-1]
    latest_timestamp = pd.to_datetime(latest_row["timestamp"])
    predicted_maintenance_date = latest_timestamp + timedelta(days=round(predicted_rul))
    maintenance_date_earliest = (
        latest_timestamp + timedelta(days=round(rul_lower)) if rul_lower is not None else None
    )
    maintenance_date_latest = (
        latest_timestamp + timedelta(days=round(rul_upper)) if rul_upper is not None else None
    )

    return {
        "predicted_rul_cycles": round(predicted_rul, 1),
        "rul_lower_cycles": rul_lower,
        "rul_upper_cycles": rul_upper,
        "health_score": health_score,
        "status": status,
        "latest_cycle": int(latest_row["cycle"]),
        "latest_timestamp": latest_timestamp,
        "predicted_maintenance_date": predicted_maintenance_date,
        "maintenance_date_earliest": maintenance_date_earliest,
        "maintenance_date_latest": maintenance_date_latest,
        "top_factors": factors,
        "confidence": get_confidence(),
        "data_drift": get_data_drift(asset_df),
    }
