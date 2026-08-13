"""
Equipment health / Remaining Useful Life (RUL) model.

Trains a regression model that predicts how many operating cycles remain
before an asset needs maintenance, from its current + recent sensor
readings. This is what turns the Maintenance Agent's rule-based alerts
(threshold checks) into genuine predictive maintenance (ML) rather than
purely reactive/rule-based monitoring — mirrors the honesty bar set by the
Energy module's forecasting model.

Data:
  - TRAIN: maintenance_train_readings.csv (full run-to-failure trajectories,
    100 engines/assets) — true RUL is exact here (max_cycle - cycle).
  - TEST (held out, genuinely never seen during training): NASA's own
    official test_FD001.txt + RUL_FD001.txt answer key. These are DIFFERENT
    engines from training, each trajectory truncated mid-life — exactly the
    situation the model needs to handle in production (we don't get to see
    an asset run to failure before predicting its RUL).

RUL is clipped at 125 cycles (standard C-MAPSS practice — see
build_maintenance_dataset.py docstring): far from failure, RUL doesn't
correlate cleanly with sensor readings anyway (the asset just looks
"healthy" regardless of exactly how healthy), so asking a regressor to
distinguish RUL=300 from RUL=280 is a much harder and less useful problem
than "healthy (>=125) vs how many cycles until it isn't."

Compares three algorithms, reports HONEST held-out metrics (MAE in cycles,
R^2) against a naive baseline (predict the training set's mean clipped RUL
for every asset, regardless of its actual sensor readings) — same "don't
hide a weak number" policy as the Energy forecast models.

Usage:
    cd backend && python ml_models/maintenance/train_health_model.py
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
TRAIN_CSV = DATA_DIR / "processed" / "maintenance_train_readings.csv"
RAW_DIR = DATA_DIR / "raw_maintenance"
MODEL_DIR = Path(__file__).resolve().parent
METRICS_PATH = MODEL_DIR / "model_metrics.json"
MODEL_PATH = MODEL_DIR / "health_rul_model.pkl"
SCATTER_PATH = MODEL_DIR / "prediction_scatter.json"

RUL_CLIP = 125
SENSOR_COLS = [
    "temp_stage1_c", "temp_stage2_c", "temp_stage3_c", "pressure_kpa",
    "vibration_index", "flow_rate", "efficiency_ratio", "bleed_load",
]
ROLLING_COLS = ["efficiency_ratio", "vibration_index"]
FEATURE_COLS = ["cycle"] + SENSOR_COLS + [f"{c}_roll_mean5" for c in ROLLING_COLS] + [f"{c}_roll_std5" for c in ROLLING_COLS]


def add_rolling_features(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    df = df.sort_values([group_col, "cycle"]).reset_index(drop=True)
    for col in ROLLING_COLS:
        df[f"{col}_roll_mean5"] = df.groupby(group_col)[col].transform(lambda s: s.rolling(5, min_periods=1).mean())
        df[f"{col}_roll_std5"] = df.groupby(group_col)[col].transform(lambda s: s.rolling(5, min_periods=1).std().fillna(0))
    return df


def load_train() -> pd.DataFrame:
    df = pd.read_csv(TRAIN_CSV)
    df = add_rolling_features(df, "asset_id")
    return df


COLS_RAW = ["unit_nr", "cycle", "setting1", "setting2", "setting3"] + [f"s{i}" for i in range(1, 22)]
RAW_RENAME = {
    "s2": "temp_stage1_c", "s3": "temp_stage2_c", "s4": "temp_stage3_c",
    "s7": "pressure_kpa", "s11": "vibration_index", "s12": "flow_rate",
    "s15": "efficiency_ratio", "s21": "bleed_load",
}


def load_official_test() -> pd.DataFrame:
    """NASA's real held-out test set — different engines than training,
    each truncated before failure. RUL_FD001.txt gives the true remaining
    cycles as of each engine's LAST recorded row (that's the only labeled
    point NASA provides for the test set)."""
    raw = pd.read_csv(RAW_DIR / "test_FD001.txt", sep=r"\s+", header=None, names=COLS_RAW)
    raw = raw.rename(columns=RAW_RENAME)[["unit_nr", "cycle"] + list(RAW_RENAME.values())]
    raw = add_rolling_features(raw, "unit_nr")

    rul_answer = pd.read_csv(RAW_DIR / "RUL_FD001.txt", header=None, names=["true_rul_at_last_cycle"])
    rul_answer["unit_nr"] = rul_answer.index + 1

    last_rows = raw.sort_values(["unit_nr", "cycle"]).groupby("unit_nr").tail(1).reset_index(drop=True)
    merged = last_rows.merge(rul_answer, on="unit_nr")
    merged["true_rul_cycles"] = merged["true_rul_at_last_cycle"].clip(upper=RUL_CLIP)
    return merged


def train_and_evaluate():
    train_df = load_train()
    X_train, y_train = train_df[FEATURE_COLS], train_df["true_rul_cycles"]

    test_df = load_official_test()
    X_test, y_test = test_df[FEATURE_COLS], test_df["true_rul_cycles"]

    naive_pred = np.full(len(y_test), y_train.mean())
    naive_mae = mean_absolute_error(y_test, naive_pred)

    candidates = {
        "linear_regression": LinearRegression(),
        "random_forest": RandomForestRegressor(n_estimators=200, max_depth=10, random_state=42, n_jobs=-1),
        "gradient_boosting": GradientBoostingRegressor(n_estimators=200, max_depth=3, random_state=42),
    }

    results = {}
    best_name, best_model, best_mae = None, None, float("inf")
    preds_by_model = {}
    for name, model in candidates.items():
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        preds_by_model[name] = preds
        mae = mean_absolute_error(y_test, preds)
        r2 = r2_score(y_test, preds)
        results[name] = {
            "held_out_test_mae_cycles": round(float(mae), 2),
            "held_out_test_r2": round(float(r2), 3),
        }
        if mae < best_mae:
            best_name, best_model, best_mae = name, model, mae

    improvement_pct = round((naive_mae - best_mae) / naive_mae * 100, 1)

    feature_importances = None
    if hasattr(best_model, "feature_importances_"):
        feature_importances = {
            f: round(float(imp), 4)
            for f, imp in sorted(zip(FEATURE_COLS, best_model.feature_importances_), key=lambda x: -x[1])
        }

    metrics = {
        "rul_clip_cycles": RUL_CLIP,
        "naive_baseline": {
            "strategy": "predict training-set mean clipped RUL for every asset",
            "mae_cycles": round(float(naive_mae), 2),
        },
        "best_model": best_name,
        "improvement_over_naive_pct": improvement_pct,
        "all_models": results,
        "feature_importances_best_model": feature_importances,
        "n_train_rows": len(train_df),
        "n_train_engines": train_df["asset_id"].nunique(),
        "n_test_engines_held_out": len(test_df),
        "note": (
            "Held-out test set is NASA's official test_FD001 + RUL_FD001 answer key — "
            "engines never seen during training, each truncated mid-life. Reported as-is."
        ),
    }

    joblib.dump({"model": best_model, "model_name": best_name, "features": FEATURE_COLS, "rul_clip": RUL_CLIP}, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2))

    # Actual-vs-predicted RUL scatter for the winning model, on all 100
    # held-out test engines (small enough to not need subsampling) — same
    # y=x diagonal diagnostic as the Energy forecast models.
    best_preds = preds_by_model[best_name]
    scatter = {
        "model": best_name,
        "r2": round(float(r2_score(y_test, best_preds)), 3),
        "unit": "cycles (operating days)",
        "points": [
            {"actual": round(float(a), 1), "predicted": round(float(p), 1)}
            for a, p in zip(y_test.values, best_preds)
        ],
    }
    SCATTER_PATH.write_text(json.dumps(scatter, indent=2))

    print(f"Best model: {best_name}  (MAE {best_mae:.2f} cycles vs naive {naive_mae:.2f} cycles, "
          f"{improvement_pct}% improvement)")
    print(f"Saved model -> {MODEL_PATH}")
    print(f"Saved metrics -> {METRICS_PATH}")
    print(f"Saved prediction scatter data -> {SCATTER_PATH}")
    return metrics


if __name__ == "__main__":
    train_and_evaluate()
