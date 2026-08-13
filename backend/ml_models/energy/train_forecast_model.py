"""
Energy consumption forecasting — MULTI-HORIZON.

Trains a SEPARATE model for each forecast horizon (1h, 6h, 24h) rather than
trying to force one model to be good at all of them. This is standard
practice in real forecasting systems: a model tuned for "next hour" (where
the current reading is highly informative) is a different problem than
"next day" (where time-of-day/weather/occupancy patterns dominate and the
current reading matters much less).

For EACH horizon, three algorithms are trained and compared using:
  1. A held-out, time-ordered test split (train on earlier data, test on
     later data — never shuffled, since shuffling a time series leaks
     future information into training).
  2. TimeSeriesSplit cross-validation (5 folds) for a more robust accuracy
     estimate than a single train/test split alone.
  3. Comparison against a naive baseline appropriate to that horizon
     ("predict no change from now" for 1h; "predict same value as this
     time yesterday" for 24h — a stronger, fairer baseline at longer
     horizons where "no change" is a weak strawman).

Design note on WHY 1h/6h/24h and not just one model: predicting the very
next 15-min reading from the previous one is close to trivial on this
dataset (consecutive readings were produced via interpolation between real
hourly source points, so lag-1 alone gives a near-perfect answer — an
artifact of upsampling, not real forecasting skill). Multiple honest
horizons, each evaluated against its own fair baseline, is a more
defensible ML demonstration than one cherry-picked easy number.

Usage:
    python ml_models/energy/train_forecast_model.py

Outputs (per horizon):
    ml_models/energy/consumption_forecast_model_{horizon}.pkl
    ml_models/energy/model_metrics.json   (all horizons, one file)
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, r2_score
from sklearn.model_selection import TimeSeriesSplit

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "energy_readings_raw.csv"
MODEL_DIR = Path(__file__).resolve().parent
METRICS_PATH = MODEL_DIR / "model_metrics.json"
SCATTER_PATH = MODEL_DIR / "prediction_scatter.json"

STEPS_PER_HOUR = 4  # 15-min data
HORIZONS = {
    "1h": 1 * STEPS_PER_HOUR,
    "6h": 6 * STEPS_PER_HOUR,
    "24h": 24 * STEPS_PER_HOUR,
}

BASE_FEATURE_COLS = [
    "hour", "day_of_week", "is_weekend", "month",
    "outdoor_temp_c", "occupancy_count",
    "kwh_now", "kwh_rolling_mean_4h", "kwh_rolling_std_4h",
    "kwh_same_hour_yesterday",
]


def load_base_df() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["month"] = df["timestamp"].dt.month

    # Features knowable AT prediction time t only — no future leakage.
    df["kwh_now"] = df["total_kwh"]
    df["kwh_rolling_mean_4h"] = df["total_kwh"].rolling(16).mean()
    df["kwh_rolling_std_4h"] = df["total_kwh"].rolling(16).std()
    # Same time-of-day, previous day — a genuinely useful feature at longer
    # horizons (daily seasonality), and doubles as the fair 24h baseline.
    df["kwh_same_hour_yesterday"] = df["total_kwh"].shift(24 * STEPS_PER_HOUR)

    return df


def build_target(df: pd.DataFrame, horizon_steps: int) -> pd.DataFrame:
    work = df.copy()
    work["target"] = work["total_kwh"].shift(-horizon_steps)
    work = work.dropna(subset=BASE_FEATURE_COLS + ["target"]).reset_index(drop=True)
    return work


def evaluate_with_cv(model, X_train, y_train, n_splits=5):
    """TimeSeriesSplit cross-validation — folds always train on the past
    and validate on the future within the training set, never shuffled."""
    tscv = TimeSeriesSplit(n_splits=n_splits)
    fold_maes = []
    for train_idx, val_idx in tscv.split(X_train):
        model.fit(X_train.iloc[train_idx], y_train.iloc[train_idx])
        preds = model.predict(X_train.iloc[val_idx])
        fold_maes.append(mean_absolute_error(y_train.iloc[val_idx], preds))
    return float(np.mean(fold_maes)), float(np.std(fold_maes))


def train_horizon(horizon_name: str, horizon_steps: int, base_df: pd.DataFrame) -> dict:
    df = build_target(base_df, horizon_steps)
    X, y = df[BASE_FEATURE_COLS], df["target"]

    split_idx = int(len(df) * 0.85)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    candidates = {
        "linear_regression": LinearRegression(),
        "random_forest": RandomForestRegressor(n_estimators=150, max_depth=10, random_state=42, n_jobs=-1),
        "gradient_boosting": GradientBoostingRegressor(n_estimators=150, max_depth=3, random_state=42),
    }

    results = {}
    best_name, best_model, best_mae = None, None, float("inf")
    preds_by_model = {}

    for name, model in candidates.items():
        cv_mae, cv_std = evaluate_with_cv(model, X_train, y_train)

        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        preds_by_model[name] = preds
        test_mae = mean_absolute_error(y_test, preds)
        test_mape = mean_absolute_percentage_error(y_test, preds)
        test_r2 = r2_score(y_test, preds)

        results[name] = {
            "held_out_test_mae_kwh": round(test_mae, 2),
            "held_out_test_mape_pct": round(test_mape * 100, 2),
            "held_out_test_r2": round(test_r2, 4),
            "cv_mae_kwh_mean": round(cv_mae, 2),
            "cv_mae_kwh_std": round(cv_std, 2),
        }
        print(f"  {name:20s} test_MAE={test_mae:6.2f} kWh  cv_MAE={cv_mae:6.2f}±{cv_std:.2f}  R2={test_r2:.4f}")

        if test_mae < best_mae:
            best_name, best_model, best_mae = name, model, test_mae

    # Two baselines, since "no change" gets weaker as horizon grows:
    naive_flat_mae = mean_absolute_error(y_test, X_test["kwh_now"].values)
    naive_daily_mae = mean_absolute_error(y_test, X_test["kwh_same_hour_yesterday"].values)
    best_baseline_mae = min(naive_flat_mae, naive_daily_mae)

    print(f"  {'naive_flat (=now)':20s} MAE={naive_flat_mae:6.2f} kWh")
    print(f"  {'naive_daily (=yday)':20s} MAE={naive_daily_mae:6.2f} kWh")
    print(f"  -> Best: {best_name}, {round((1 - best_mae/best_baseline_mae)*100, 1)}% better than best naive baseline\n")

    # Feature importance for the winning model, if it's tree-based —
    # concrete interpretability, not just an accuracy number.
    feature_importance = None
    if hasattr(best_model, "feature_importances_"):
        feature_importance = {
            col: round(float(imp), 4)
            for col, imp in sorted(
                zip(BASE_FEATURE_COLS, best_model.feature_importances_),
                key=lambda x: -x[1]
            )
        }

    # Actual-vs-predicted scatter for the winning model — the classic
    # "how reliable is this regression really" diagnostic: points hugging
    # the y=x diagonal mean accurate predictions, a wide scattered cloud
    # means the model is unreliable at this horizon. Subsampled evenly
    # across the (time-ordered) test set so the chart isn't overplotted.
    best_preds = preds_by_model[best_name]
    n_points = min(150, len(y_test))
    idx = np.linspace(0, len(y_test) - 1, n_points).astype(int)
    scatter_points = [
        {"actual": round(float(y_test.values[i]), 2), "predicted": round(float(best_preds[i]), 2)}
        for i in idx
    ]

    model_path = MODEL_DIR / f"consumption_forecast_model_{horizon_name}.pkl"
    joblib.dump({
        "model": best_model,
        "features": BASE_FEATURE_COLS,
        "model_name": best_name,
        "horizon_steps": horizon_steps,
        "horizon_name": horizon_name,
    }, model_path)

    return {
        "horizon": horizon_name,
        "horizon_steps": horizon_steps,
        "best_model": best_name,
        "all_models": results,
        "naive_flat_mae_kwh": round(naive_flat_mae, 2),
        "naive_daily_mae_kwh": round(naive_daily_mae, 2),
        "improvement_over_best_naive_pct": round((1 - best_mae / best_baseline_mae) * 100, 1),
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "feature_importance": feature_importance,
        "model_file": model_path.name,
        "scatter_points": scatter_points,
    }


def train():
    base_df = load_base_df()
    all_results = {}
    scatter_by_horizon = {}

    for horizon_name, horizon_steps in HORIZONS.items():
        print(f"=== Horizon: {horizon_name} ({horizon_steps} steps) ===")
        result = train_horizon(horizon_name, horizon_steps, base_df)
        scatter_by_horizon[horizon_name] = {
            "model": result["best_model"],
            "r2": result["all_models"][result["best_model"]]["held_out_test_r2"],
            "points": result.pop("scatter_points"),
        }
        all_results[horizon_name] = result

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps({
        "features": BASE_FEATURE_COLS,
        "horizons": all_results,
    }, indent=2))
    SCATTER_PATH.write_text(json.dumps(scatter_by_horizon, indent=2))
    print(f"Saved combined metrics -> {METRICS_PATH}")
    print(f"Saved prediction scatter data -> {SCATTER_PATH}")


if __name__ == "__main__":
    train()
