"""
Cost analytics: runs the trained anomaly detectors (see
ml_models/cost/train_anomaly_model.py) and forecast model (see
ml_models/cost/train_forecast_model.py) against the current record set,
and computes rule-based budget-compliance and vendor-concentration KPIs
(same "ML where it earns its keep, rules where they're clearer" mix the
other agents use — e.g. Energy's rule-based waste detection alongside
its ML forecast).
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from app.utils.drift_detection import compute_drift

MODEL_DIR = Path(__file__).resolve().parents[2] / "ml_models" / "cost"
ANOMALY_MODEL_PATH = MODEL_DIR / "anomaly_model.pkl"
ANOMALY_METRICS_PATH = MODEL_DIR / "model_metrics.json"
LOF_METRICS_PATH = MODEL_DIR / "lof_model_metrics.json"
FORECAST_MODEL_PATH = MODEL_DIR / "forecast_model.pkl"
FORECAST_METRICS_PATH = MODEL_DIR / "forecast_model_metrics.json"

_cache = {}


def is_model_available() -> bool:
    return ANOMALY_MODEL_PATH.exists() and FORECAST_MODEL_PATH.exists()


def _load(path: Path, key: str):
    if key not in _cache:
        _cache[key] = joblib.load(path)
    return _cache[key]


def get_anomaly_model_confidence() -> dict:
    if not ANOMALY_METRICS_PATH.exists():
        return {"available": False}
    return {"available": True, **json.loads(ANOMALY_METRICS_PATH.read_text())}


def get_anomaly_comparison_confidence() -> dict:
    if not LOF_METRICS_PATH.exists():
        return {"available": False}
    return {"available": True, **json.loads(LOF_METRICS_PATH.read_text())}


def get_forecast_confidence() -> dict:
    if not FORECAST_METRICS_PATH.exists():
        return {"available": False}
    return {"available": True, **json.loads(FORECAST_METRICS_PATH.read_text())}


def get_data_drift(records_df: pd.DataFrame) -> dict:
    """Does the CURRENT spend data (bundled dataset, or an uploaded one)
    still look like what the anomaly detector was trained on — see
    app/utils/drift_detection.py.

    Uses log1p(amount_inr), not raw amount_inr: invoice amounts are
    heavily right-skewed (this dataset mixes small purchase orders with
    multi-crore capital-works tenders), which makes the training set's own
    raw standard deviation enormous — a genuinely different dataset's mean
    could differ by orders of magnitude and still score under the z>=2
    threshold on raw values. log1p compresses that skew enough for the
    same z-score check to actually mean something, the same reason the
    anomaly detector itself trains on log_amount rather than raw amount.
    """
    if not ANOMALY_METRICS_PATH.exists() or records_df.empty:
        return {"available": False}
    metrics = json.loads(ANOMALY_METRICS_PATH.read_text())
    training_dist = metrics.get("training_distribution")
    if not training_dist:
        return {"available": False}
    current_means = {}
    if "log_amount_inr" in training_dist and "amount_inr" in records_df.columns and not records_df["amount_inr"].dropna().empty:
        current_means["log_amount_inr"] = float(np.log1p(records_df["amount_inr"]).mean())
    return compute_drift(current_means, training_dist)


# ---- Anomaly scoring -----------------------------------------------------

def _engineer_anomaly_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["log_amount"] = np.log1p(df["amount_inr"])
    cat_median = df.groupby("category")["amount_inr"].transform("median")
    df["amount_vs_category_median"] = df["amount_inr"] / cat_median.clip(lower=1)
    vendor_counts = df["vendor_id"].map(df["vendor_id"].value_counts())
    df["vendor_order_count"] = vendor_counts
    df["is_new_vendor"] = (vendor_counts <= 1).astype(int)
    df["day_of_month"] = df["date"].dt.day
    df["is_month_end_batch"] = (df["day_of_month"] >= 25).astype(int)
    df["category_code"] = df["category"].astype("category").cat.codes
    return df


def score_records(records_df: pd.DataFrame) -> pd.DataFrame:
    """Adds `flagged` (bool) + `anomaly_score` (higher = more unusual)
    columns using the live IsolationForest."""
    if records_df.empty:
        return records_df
    bundle = _load(ANOMALY_MODEL_PATH, "anomaly")
    model, scaler, features = bundle["model"], bundle["scaler"], bundle["features"]
    engineered = _engineer_anomaly_features(records_df)
    X = scaler.transform(engineered[features])
    engineered["flagged"] = model.predict(X) == -1
    engineered["anomaly_score"] = (-model.score_samples(X)).round(3)
    return engineered


def top_flagged_records(scored_df: pd.DataFrame, limit: int = 15) -> list[dict]:
    if scored_df.empty or "flagged" not in scored_df:
        return []
    flagged = scored_df[scored_df["flagged"]].sort_values("anomaly_score", ascending=False).head(limit)
    return [{
        "record_id": r.record_id, "vendor_id": r.vendor_id, "vendor_name": r.vendor_name,
        "category": r.category, "date": r.date, "amount_inr": r.amount_inr,
        "anomaly_score": float(r.anomaly_score),
    } for r in flagged.itertuples(index=False)]


# ---- Forecast --------------------------------------------------------

def forecast_trend(records_df: pd.DataFrame) -> dict:
    """Predicts the forward 3-week rolling-average spend trend using the
    live model. See ml_models/cost/train_forecast_model.py for why the
    target is a smoothed trend rather than a single noisy week."""
    if not FORECAST_MODEL_PATH.exists() or records_df.empty:
        return {"available": False}
    bundle = _load(FORECAST_MODEL_PATH, "forecast")
    model, features = bundle["model"], bundle["features"]

    df = records_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["week"] = df["date"].dt.to_period("W").apply(lambda p: p.start_time)
    weekly = df.groupby("week")["amount_inr"].sum().reset_index().sort_values("week")
    weekly = weekly.set_index("week").asfreq("W-MON", fill_value=0.0).reset_index()
    weekly.columns = ["week", "total_spend_inr"]
    weekly["log_spend"] = np.log1p(weekly["total_spend_inr"])

    if len(weekly) < 3:
        return {"available": False}

    latest = weekly.iloc[-1]
    lag1 = weekly["log_spend"].iloc[-1]
    lag2 = weekly["log_spend"].iloc[-2]
    roll3_median = weekly["log_spend"].iloc[-3:].median()
    week_of_year = int(pd.Timestamp(latest["week"]).isocalendar()[1])

    X = pd.DataFrame([{"lag1": lag1, "lag2": lag2, "roll3_median": roll3_median, "week_of_year": week_of_year}])[features]
    pred_log = model.predict(X)[0]
    pred_inr = float(np.expm1(pred_log))
    current_trend = float(weekly["total_spend_inr"].iloc[-3:].mean())

    # Real weekly spend history (not just the single forward prediction) —
    # lets the dashboard actually chart "how did we get here" alongside
    # "where the model thinks we're headed", the same actual-vs-forecast
    # framing the Energy and Maintenance dashboards already use for their
    # own ML predictions. Capped to the most recent 26 weeks so the chart
    # stays legible even as more history accumulates.
    next_week = pd.Timestamp(latest["week"]) + pd.Timedelta(weeks=1)
    history = [
        {"week": str(row.week.date()), "actual_spend_inr": round(float(row.total_spend_inr), 2)}
        for row in weekly.tail(26).itertuples(index=False)
    ]

    return {
        "available": True,
        "predicted_next_3wk_avg_spend_inr": round(pred_inr, 2),
        "current_3wk_avg_spend_inr": round(current_trend, 2),
        "direction": "up" if pred_inr > current_trend * 1.05 else "down" if pred_inr < current_trend * 0.95 else "flat",
        "as_of_week": str(latest["week"].date()),
        "next_week": str(next_week.date()),
        "history": history,
        "confidence": get_forecast_confidence(),
    }


# ---- Budget compliance (rule-based) -----------------------------------

def budget_compliance(records_df: pd.DataFrame, budgets: list[dict]) -> list[dict]:
    """Current-month actual vs. assumption-based budget per category.
    See data/build_cost_dataset.py for why the budget figure is an
    assumption, not a real published one."""
    if records_df.empty:
        return []
    df = records_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    latest_month = df["date"].dt.to_period("M").max()
    current = df[df["date"].dt.to_period("M") == latest_month]
    spent_by_cat = current.groupby("category")["amount_inr"].sum().to_dict()

    out = []
    for b in budgets:
        spent = float(spent_by_cat.get(b["category"], 0.0))
        budget = b["monthly_budget_inr"]
        pct = round(100 * spent / budget, 1) if budget else 0.0
        out.append({
            "category": b["category"], "month": str(latest_month), "spent_inr": round(spent, 2),
            "budget_inr": budget, "pct_of_budget": pct,
            "status": "over" if pct > 100 else "at_risk" if pct > 85 else "on_track",
            "basis": b["basis"],
        })
    return sorted(out, key=lambda r: r["pct_of_budget"], reverse=True)


# ---- Vendor concentration (rule-based) --------------------------------

def vendor_concentration(vendors: list[dict], top_n: int = 5) -> dict:
    """What share of total spend sits with the top N vendors — a simple,
    interpretable 'are we over-dependent on one supplier' signal for
    'optimize vendor utilization'."""
    if not vendors:
        return {"top_vendors": [], "top_n_share_pct": 0.0, "total_spend_inr": 0.0}
    total = sum(v["total_spend_inr"] for v in vendors)
    ranked = sorted(vendors, key=lambda v: v["total_spend_inr"], reverse=True)
    top = ranked[:top_n]
    top_share = round(100 * sum(v["total_spend_inr"] for v in top) / total, 1) if total else 0.0
    return {
        "top_vendors": [{
            "vendor_id": v["vendor_id"], "vendor_name": v["vendor_name"],
            "primary_category": v["primary_category"], "total_spend_inr": round(v["total_spend_inr"], 2),
            "order_count": v["order_count"], "share_pct": round(100 * v["total_spend_inr"] / total, 1) if total else 0.0,
        } for v in top],
        "top_n_share_pct": top_share,
        "total_spend_inr": round(total, 2),
    }


def spend_summary(records_df: pd.DataFrame) -> dict:
    if records_df.empty:
        return {"total_spend_inr": 0.0, "record_count": 0, "vendor_count": 0, "category_count": 0}
    return {
        "total_spend_inr": round(float(records_df["amount_inr"].sum()), 2),
        "record_count": int(len(records_df)),
        "vendor_count": int(records_df["vendor_id"].nunique()),
        "category_count": int(records_df["category"].nunique()),
        "date_range": [str(records_df["date"].min().date()), str(records_df["date"].max().date())],
    }


def category_breakdown(records_df: pd.DataFrame) -> list[dict]:
    if records_df.empty:
        return []
    total = records_df["amount_inr"].sum()
    by_cat = records_df.groupby("category")["amount_inr"].sum().sort_values(ascending=False)
    return [{"category": cat, "spend_inr": round(float(v), 2), "pct_of_total": round(100 * v / total, 1)} for cat, v in by_cat.items()]
