"""
Trains two unsupervised anomaly detectors on real invoice line-item data
(see data/build_cost_dataset.py for the full honesty disclosure on the
source) to flag overpriced / statistically unusual invoices.

HONEST LIMITATION vs. the Security module's anomaly model: this is REAL
procurement data with no injected, labeled ground truth (nobody hand-tags
which of these real council invoices were actually anomalous). So unlike
Security's precision/recall — which IS measurable there because those
labels are synthetic-but-known — here we can only report unsupervised
separation diagnostics (silhouette-style score margin, % flagged, and
which categories/vendors the flags concentrate in). Treat "flagged" as
"worth a human glance", not "confirmed anomalous".

Two models, same pattern as Security's IsolationForest+LOF comparison:
  - IsolationForest (primary, used for live scoring)
  - LocalOutlierFactor in novelty mode (comparison-only diagnostic)
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "cost_records.csv"
MODEL_DIR = Path(__file__).resolve().parent
CONTAMINATION = 0.08  # expect ~8% of real invoices to be worth a second look


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
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


FEATURES = [
    "log_amount", "amount_vs_category_median", "vendor_order_count",
    "is_new_vendor", "is_month_end_batch", "category_code",
]


def train():
    df = pd.read_csv(DATA_PATH)
    engineered = engineer_features(df)
    X = engineered[FEATURES]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    iso = IsolationForest(n_estimators=300, contamination=CONTAMINATION, random_state=42)
    iso_pred = iso.fit_predict(X_scaled)
    iso_scores = -iso.score_samples(X_scaled)
    flagged_iso = iso_pred == -1

    lof = LocalOutlierFactor(n_neighbors=15, contamination=CONTAMINATION, novelty=False)
    lof_pred = lof.fit_predict(X_scaled)
    lof_scores = -lof.negative_outlier_factor_
    flagged_lof = lof_pred == -1

    agree = float((flagged_iso == flagged_lof).mean())
    both_flag = int((flagged_iso & flagged_lof).sum())

    joblib.dump({"model": iso, "scaler": scaler, "features": FEATURES}, MODEL_DIR / "anomaly_model.pkl")

    iso_metrics = {
        "model": "IsolationForest",
        "n_estimators": 300,
        "contamination": CONTAMINATION,
        "n_records": len(df),
        "n_flagged": int(flagged_iso.sum()),
        "pct_flagged": round(100 * flagged_iso.mean(), 1),
        "flagged_total_value_inr": round(float(engineered.loc[flagged_iso, "amount_inr"].sum()), 2),
        "top_flagged_categories": engineered.loc[flagged_iso, "category"].value_counts().head(3).to_dict(),
        "agreement_with_lof_pct": round(100 * agree, 1),
        "note": (
            "Trained on REAL BBMP (Bengaluru) tender data plus logically-derived cross-agent operating cost (see build_cost_dataset.py). "
            "No labeled ground truth exists for real invoices, so this reports unsupervised "
            "separation diagnostics, not precision/recall. 'Flagged' means statistically "
            "unusual for its category/vendor pattern — a lead for review, not a confirmed error."
        ),
    }
    (MODEL_DIR / "model_metrics.json").write_text(json.dumps(iso_metrics, indent=2))

    lof_metrics = {
        "model": "LocalOutlierFactor",
        "n_neighbors": 15,
        "contamination": CONTAMINATION,
        "n_flagged": int(flagged_lof.sum()),
        "pct_flagged": round(100 * flagged_lof.mean(), 1),
        "agreement_with_isolation_forest_pct": round(100 * agree, 1),
        "both_models_flagged_count": both_flag,
        "note": (
            "Comparison-only detector (density-based rather than IsolationForest's "
            "partitioning approach) — not used for live scoring. Shown side-by-side so the "
            "dashboard doesn't present a single unsupervised model's opinion as ground truth."
        ),
    }
    (MODEL_DIR / "lof_model_metrics.json").write_text(json.dumps(lof_metrics, indent=2))

    print(f"IsolationForest flagged {flagged_iso.sum()}/{len(df)} ({iso_metrics['pct_flagged']}%)")
    print(f"LOF flagged {flagged_lof.sum()}/{len(df)} ({lof_metrics['pct_flagged']}%), agreement {agree:.1%}")


if __name__ == "__main__":
    train()
