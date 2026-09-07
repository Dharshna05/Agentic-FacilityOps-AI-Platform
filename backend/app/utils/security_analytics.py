"""
Security analytics: runs the trained Isolation Forest (see
ml_models/security/train_anomaly_model.py) against the current event
stream, and rolls the result up into building-wide KPIs. Also exposes the
model's own honest offline evaluation (precision/recall/F1 against injected
synthetic ground truth) so the dashboard can show real confidence, not a
claimed one.
"""
import json
from pathlib import Path

import joblib
import pandas as pd

from app.utils.drift_detection import compute_drift

MODEL_DIR = Path(__file__).resolve().parents[2] / "ml_models" / "security"
MODEL_PATH = MODEL_DIR / "anomaly_model.pkl"
METRICS_PATH = MODEL_DIR / "model_metrics.json"
LOF_METRICS_PATH = MODEL_DIR / "lof_model_metrics.json"
RF_REFERENCE_METRICS_PATH = MODEL_DIR / "rf_reference_metrics.json"

RISK_ENCODE = {"low": 0, "medium": 1, "high": 2}
_bundle_cache = None


def _load_model():
    global _bundle_cache
    if _bundle_cache is None:
        _bundle_cache = joblib.load(MODEL_PATH)
    return _bundle_cache


def is_model_available() -> bool:
    return MODEL_PATH.exists()


def get_model_confidence() -> dict:
    if not METRICS_PATH.exists():
        return {"available": False}
    m = json.loads(METRICS_PATH.read_text())
    return {
        "available": True,
        "model_used": m.get("model"),
        "precision": m.get("precision"),
        "recall": m.get("recall"),
        "f1": m.get("f1"),
        "note": m.get("note"),
    }


def get_data_drift(events_df: pd.DataFrame) -> dict:
    """Does the CURRENT access-log data (bundled dataset, or an uploaded
    one) still look like what the anomaly detector was trained on — see
    app/utils/drift_detection.py. Computed on the same engineered features
    the model itself uses (hour_of_day, is_business_hours, access_denied,
    etc.), not raw columns, so it reflects what the model actually sees."""
    if not METRICS_PATH.exists():
        return {"available": False}
    metrics = json.loads(METRICS_PATH.read_text())
    training_dist = metrics.get("training_distribution")
    if not training_dist:
        return {"available": False}

    engineered = _engineer_features(events_df)
    current_means = {
        col: float(engineered[col].mean()) if col in engineered.columns and not engineered[col].dropna().empty else None
        for col in training_dist
    }
    return compute_drift(current_means, training_dist)


def get_comparison_model_confidence() -> dict:
    """Second, genuinely-trained anomaly detector (Local Outlier Factor)
    for honest side-by-side comparison against the production Isolation
    Forest — same pattern as Occupancy's CNN-vs-Logistic-Regression panel.
    Not used for live scoring; see the note for why."""
    if not LOF_METRICS_PATH.exists():
        return {"available": False}
    m = json.loads(LOF_METRICS_PATH.read_text())
    return {
        "available": True,
        "model_used": m.get("model"),
        "precision": m.get("precision"),
        "recall": m.get("recall"),
        "f1": m.get("f1"),
        "detection_rate_by_anomaly_type": m.get("detection_rate_by_anomaly_type"),
        "note": m.get("note"),
    }


def get_supervised_reference_confidence() -> dict:
    """A THIRD model — a supervised RandomForest trained WITH the labels
    via cross-validation, kept only as an honest reference point (never
    live-scored). See ml_models/security/train_anomaly_model.py's
    train_supervised_reference() docstring for why."""
    if not RF_REFERENCE_METRICS_PATH.exists():
        return {"available": False}
    m = json.loads(RF_REFERENCE_METRICS_PATH.read_text())
    return {
        "available": True,
        "model_used": m.get("model"),
        "precision": m.get("precision"),
        "recall": m.get("recall"),
        "f1": m.get("f1"),
        "detection_rate_by_anomaly_type": m.get("detection_rate_by_anomaly_type"),
        "note": m.get("note"),
    }


def _engineer_features(events_df: pd.DataFrame, first_visit_map: dict | None = None) -> pd.DataFrame:
    df = events_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["hour_of_day"] = df["timestamp"].dt.hour + df["timestamp"].dt.minute / 60
    df["is_business_hours"] = ((df["hour_of_day"] >= 8.5) & (df["hour_of_day"] <= 18.5) & (df["timestamp"].dt.dayofweek < 5)).astype(int)
    df["is_weekend"] = (df["timestamp"].dt.dayofweek >= 5).astype(int)
    df["risk_level_enc"] = df["risk_level"].map(RISK_ENCODE).fillna(0)
    df["access_denied"] = (~df["access_granted"]).astype(int)
    df["recent_denials_by_employee"] = (
        df.groupby("employee_id")["access_denied"]
        .transform(lambda s: s.rolling(10, min_periods=1).sum())
    )
    # Time-windowed denial burst feature — same as training (see
    # ml_models/security/train_anomaly_model.py's accuracy-pass note on
    # why the event-count window alone can dilute a genuine burst).
    df = df.reset_index(drop=True)
    df["_row_id"] = df.index
    windowed = []
    for _, g in df.groupby("employee_id", sort=False):
        g = g.sort_values("timestamp")
        s = g.set_index("timestamp")["access_denied"].rolling("5min").sum()
        windowed.append(pd.DataFrame({"_row_id": g["_row_id"].values, "recent_denials_5min_by_employee": s.values}))
    windowed_df = pd.concat(windowed).set_index("_row_id").sort_index()
    df["recent_denials_5min_by_employee"] = windowed_df["recent_denials_5min_by_employee"].values
    df = df.drop(columns=["_row_id"])
    # Same novelty feature as training (see ml_models/security/train_anomaly_model.py) —
    # has this employee ever used this access point before? When a
    # first_visit_map (from the FULL event history, not just this scored
    # window) is supplied, use the true first-visit timestamp; otherwise
    # fall back to novelty-within-this-window only (used during offline
    # training, where the whole dataset IS the window).
    if first_visit_map is not None:
        df["_first_visit_ts"] = df.apply(
            lambda r: first_visit_map.get((r["employee_id"], r["access_point_id"])), axis=1
        )
        df["is_novel_access_point_for_employee"] = (df["timestamp"] <= df["_first_visit_ts"]).astype(int)
        df = df.drop(columns=["_first_visit_ts"])
    else:
        df["_visit_number"] = df.groupby(["employee_id", "access_point_id"]).cumcount()
        df["is_novel_access_point_for_employee"] = (df["_visit_number"] == 0).astype(int)
        df = df.drop(columns=["_visit_number"])

    # Interaction feature isolating first-ever visit to a HIGH-risk door
    # specifically — same as training, more specific than either input
    # feature alone for the restricted-zone pattern.
    df["novel_high_risk_access"] = df["is_novel_access_point_for_employee"] * df["risk_level_enc"].clip(upper=1) * (df["risk_level"] == "high").astype(int)
    return df


def score_events(events_df: pd.DataFrame, first_visit_map: dict | None = None) -> pd.DataFrame:
    """Runs the live Isolation Forest against the given events and adds
    `flagged` (bool) + `anomaly_score` (higher = more anomalous) columns.
    Pass first_visit_map (see security_service.get_first_visit_timestamps)
    for an accurate novelty feature against full history rather than just
    this scored window."""
    if events_df.empty:
        return events_df
    bundle = _load_model()
    model, features = bundle["model"], bundle["features"]
    engineered = _engineer_features(events_df, first_visit_map)
    X = engineered[features]
    raw_pred = model.predict(X)
    scores = -model.score_samples(X)  # flip sign: higher = more anomalous, easier to reason about
    engineered["flagged"] = raw_pred == -1
    engineered["anomaly_score"] = scores.round(3)
    return engineered


def building_security_summary(scored_events: pd.DataFrame, access_points: list[dict]) -> dict:
    if scored_events.empty:
        return {
            "access_points_monitored": len(access_points), "events_last_24h": 0,
            "denied_last_24h": 0, "flagged_last_24h": 0,
        }
    cutoff = scored_events["timestamp"].max() - pd.Timedelta(hours=24)
    recent = scored_events[scored_events["timestamp"] >= cutoff]
    return {
        "access_points_monitored": len(access_points),
        "events_last_24h": int(len(recent)),
        "denied_last_24h": int((~recent["access_granted"]).sum()),
        "flagged_last_24h": int(recent["flagged"].sum()) if "flagged" in recent else 0,
    }


def top_flagged_events(scored_events: pd.DataFrame, limit: int = 15) -> list[dict]:
    if scored_events.empty or "flagged" not in scored_events:
        return []
    flagged = scored_events[scored_events["flagged"]].sort_values("anomaly_score", ascending=False).head(limit)
    return [{
        "event_id": r.event_id,
        "access_point_id": r.access_point_id,
        "employee_id": r.employee_id,
        "timestamp": r.timestamp,
        "access_granted": bool(r.access_granted),
        "risk_level": r.risk_level,
        "anomaly_score": float(r.anomaly_score),
    } for r in flagged.itertuples(index=False)]


def access_point_heatmap(scored_events: pd.DataFrame, access_points: list[dict]) -> list[dict]:
    """One row per access point: average live anomaly score by hour-of-day
    (0-23), across all scored history available — same "when is this door
    actually risky" picture as the Occupancy heatmap, but driven by the
    Isolation Forest's real anomaly_score instead of headcount. Powers the
    Security dashboard's risk heatmap visualization."""
    out = []
    if scored_events.empty or "anomaly_score" not in scored_events:
        return [{"access_point_id": ap["access_point_id"], "risk_level": ap["risk_level"],
                  "hourly_avg_risk": [0.0] * 24} for ap in access_points]

    df = scored_events.copy()
    df["hour"] = df["timestamp"].dt.hour
    by_ap = {ap["access_point_id"]: ap for ap in access_points}

    for ap_id, ap in by_ap.items():
        sub = df[df["access_point_id"] == ap_id]
        if sub.empty:
            out.append({"access_point_id": ap_id, "risk_level": ap["risk_level"], "hourly_avg_risk": [0.0] * 24})
            continue
        hourly = sub.groupby("hour")["anomaly_score"].mean().round(3)
        out.append({
            "access_point_id": ap_id,
            "risk_level": ap["risk_level"],
            "hourly_avg_risk": [round(float(hourly.get(h, 0.0)), 3) for h in range(24)],
        })
    return out


def access_point_activity(scored_events: pd.DataFrame, access_points: list[dict]) -> list[dict]:
    """One row per access point: real event/denial/flag counts, for the
    at-a-glance risk grid (colored by static risk_level, sized/annotated by
    actual observed activity — not just the door's configured risk tier)."""
    out = []
    if scored_events.empty:
        return [{"access_point_id": ap["access_point_id"], "name": ap.get("name", ap["access_point_id"]),
                  "risk_level": ap["risk_level"], "event_count": 0, "denied_count": 0,
                  "flagged_count": 0, "avg_anomaly_score": 0.0} for ap in access_points]

    for ap in access_points:
        sub = scored_events[scored_events["access_point_id"] == ap["access_point_id"]]
        out.append({
            "access_point_id": ap["access_point_id"],
            "name": ap.get("name", ap["access_point_id"]),
            "risk_level": ap["risk_level"],
            "event_count": int(len(sub)),
            "denied_count": int((~sub["access_granted"]).sum()) if not sub.empty else 0,
            "flagged_count": int(sub["flagged"].sum()) if "flagged" in sub and not sub.empty else 0,
            "avg_anomaly_score": round(float(sub["anomaly_score"].mean()), 3) if "anomaly_score" in sub and not sub.empty else 0.0,
        })
    return out
