"""
Deep-learning RUL model — LSTM over raw sensor SEQUENCES.

Every other model in this project (including the tree-based RUL model in
train_health_model.py) predicts from a single row of HAND-ENGINEERED
features (rolling means/stds/deltas computed over a window of past
cycles — see app/utils/rul_features.py). This script instead gives an
LSTM the RAW sensor readings for the last SEQUENCE_LENGTH cycles directly,
and lets the network learn its own temporal degradation pattern instead of
us hand-crafting rolling-window features for it — the standard
architecture choice for this exact dataset (NASA C-MAPSS) in the
published literature, and the natural "go deep learning" move for a
sequential-degradation problem like this one.

TRAINING SEQUENCES: for each of the 100 training engines, every valid
sliding window of SEQUENCE_LENGTH consecutive cycles is used as one
training example (labeled with the clipped RUL AT THAT WINDOW'S LAST
CYCLE) — not just one window per engine. This is deliberate data
augmentation: it turns 100 engines' full trajectories into ~16,700
overlapping-but-distinct (sequence, RUL) training examples, which is what
makes training a sequence model on only 100 real trajectories feasible at
all.

VALIDATION (during training, for early stopping): a GROUP-LEVEL split — 15
of the 100 training engines are held out entirely (none of their windows
appear in the training side), so early stopping is judged on genuinely
unseen engines, not just unseen windows of engines the model has partly
seen elsewhere in their trajectory.

FINAL HONEST EVALUATION: the same NASA official test_FD001.txt/
RUL_FD001.txt held-out set every other model in this project is evaluated
against — different engines than training, never touched until this final
step, so the LSTM's reported number is directly comparable to the tree
model's.

HONEST COMPARISON: this script does NOT assume the LSTM wins. It loads the
tree-based model's existing held-out MAE from model_metrics.json and only
recommends switching the live model if the LSTM's held-out MAE is
genuinely lower — see the printed comparison at the end. Whichever wins,
BOTH model files are kept on disk; health_service.py picks whichever
`model_metrics.json` names as `"live_model"`.

Usage:
    cd backend && python ml_models/maintenance/train_lstm_rul_model.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.utils.rul_features import SENSOR_COLS  # noqa: E402

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
TRAIN_CSV = DATA_DIR / "processed" / "maintenance_train_readings.csv"
RAW_DIR = DATA_DIR / "raw_maintenance"
MODEL_DIR = Path(__file__).resolve().parent
METRICS_PATH = MODEL_DIR / "model_metrics.json"
LSTM_MODEL_PATH = MODEL_DIR / "health_rul_lstm.keras"
LSTM_SCALER_PATH = MODEL_DIR / "health_rul_lstm_scaler.pkl"

RUL_CLIP = 125
SEQUENCE_LENGTH = 40  # matches the tree model's tuned 35-cycle long window, rounded for a clean architecture
N_FEATURES = len(SENSOR_COLS)

COLS_RAW = ["unit_nr", "cycle", "setting1", "setting2", "setting3"] + [f"s{i}" for i in range(1, 22)]
RAW_RENAME = {
    "s2": "temp_stage1_c", "s3": "temp_stage2_c", "s4": "temp_stage3_c",
    "s7": "pressure_kpa", "s11": "vibration_index", "s12": "flow_rate",
    "s15": "efficiency_ratio", "s21": "bleed_load",
}


def build_training_sequences(train_df: pd.DataFrame):
    """Every valid SEQUENCE_LENGTH-cycle sliding window per engine, each
    labeled with the clipped RUL at that window's final cycle. Also
    returns which engine each sequence came from, so the train/validation
    split below can be done by engine (group), never splitting one
    engine's own windows across both sides."""
    sequences, labels, engine_ids = [], [], []
    for asset_id, group in train_df.sort_values("cycle").groupby("asset_id"):
        values = group[SENSOR_COLS].values
        ruls = group["true_rul_cycles"].values
        for end in range(SEQUENCE_LENGTH - 1, len(group)):
            start = end - SEQUENCE_LENGTH + 1
            sequences.append(values[start:end + 1])
            labels.append(ruls[end])
            engine_ids.append(asset_id)
    return np.array(sequences), np.array(labels, dtype=float), np.array(engine_ids)


def build_test_sequences(test_df: pd.DataFrame, official_test_raw: pd.DataFrame):
    """One sequence per NASA test engine — its LAST SEQUENCE_LENGTH cycles
    (front-padded with its own earliest reading repeated, if the engine's
    truncated trajectory is shorter than SEQUENCE_LENGTH), matching the
    single prediction point test_health_model.py's official-test loader
    evaluates against."""
    sequences = []
    for unit_nr in test_df["unit_nr"]:
        engine_rows = official_test_raw[official_test_raw["unit_nr"] == unit_nr].sort_values("cycle")
        values = engine_rows[SENSOR_COLS].values
        if len(values) >= SEQUENCE_LENGTH:
            seq = values[-SEQUENCE_LENGTH:]
        else:
            pad = np.repeat(values[:1], SEQUENCE_LENGTH - len(values), axis=0)
            seq = np.vstack([pad, values])
        sequences.append(seq)
    return np.array(sequences)


def train():
    import tensorflow as tf
    from tensorflow.keras import layers, models, callbacks

    tf.random.set_seed(42)

    train_df = pd.read_csv(TRAIN_CSV)
    X_seq, y_seq, engine_ids = build_training_sequences(train_df)
    print(f"Built {len(X_seq)} training sequences (length {SEQUENCE_LENGTH}) from {train_df['asset_id'].nunique()} engines.")

    # Group-level (by engine) validation split — 15 engines held out
    # entirely from training so early stopping reflects genuinely unseen
    # engines, not just unseen windows of a partly-seen one.
    rng = np.random.RandomState(42)
    unique_engines = np.unique(engine_ids)
    val_engines = set(rng.choice(unique_engines, size=15, replace=False))
    val_mask = np.isin(engine_ids, list(val_engines))

    X_train, y_train = X_seq[~val_mask], y_seq[~val_mask]
    X_val, y_val = X_seq[val_mask], y_seq[val_mask]
    print(f"Train sequences: {len(X_train)}  Val sequences (15 held-out engines): {len(X_val)}")

    # Fit the scaler on TRAINING sequences' timesteps only (flattened),
    # exactly like every other model in this project only fits
    # preprocessing on the training split.
    scaler = StandardScaler()
    scaler.fit(X_train.reshape(-1, N_FEATURES))
    X_train_s = scaler.transform(X_train.reshape(-1, N_FEATURES)).reshape(X_train.shape)
    X_val_s = scaler.transform(X_val.reshape(-1, N_FEATURES)).reshape(X_val.shape)

    model = models.Sequential([
        layers.Input(shape=(SEQUENCE_LENGTH, N_FEATURES)),
        layers.LSTM(64, return_sequences=True),
        layers.Dropout(0.2),
        layers.LSTM(32),
        layers.Dropout(0.2),
        layers.Dense(16, activation="relu"),
        layers.Dense(1, activation="linear"),
    ])
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3), loss="mse", metrics=["mae"])
    print(model.summary())

    early_stop = callbacks.EarlyStopping(monitor="val_mae", patience=8, restore_best_weights=True)
    history = model.fit(
        X_train_s, y_train,
        validation_data=(X_val_s, y_val),
        epochs=60, batch_size=64, callbacks=[early_stop], verbose=2,
    )
    epochs_trained = len(history.history["loss"])
    print(f"Stopped after {epochs_trained} epochs (early stopping on val_mae, patience=8).")

    # --- Final honest evaluation on NASA's official held-out test engines ---
    raw = pd.read_csv(RAW_DIR / "test_FD001.txt", sep=r"\s+", header=None, names=COLS_RAW)
    raw = raw.rename(columns=RAW_RENAME)[["unit_nr", "cycle"] + list(RAW_RENAME.values())]
    rul_answer = pd.read_csv(RAW_DIR / "RUL_FD001.txt", header=None, names=["true_rul_at_last_cycle"])
    rul_answer["unit_nr"] = rul_answer.index + 1
    rul_answer["true_rul_cycles"] = rul_answer["true_rul_at_last_cycle"].clip(upper=RUL_CLIP)

    X_test = build_test_sequences(rul_answer, raw)
    X_test_s = scaler.transform(X_test.reshape(-1, N_FEATURES)).reshape(X_test.shape)
    y_test = rul_answer["true_rul_cycles"].values

    preds = np.clip(model.predict(X_test_s, verbose=0).flatten(), 0, RUL_CLIP)
    lstm_mae = float(mean_absolute_error(y_test, preds))
    lstm_r2 = float(r2_score(y_test, preds))
    print(f"\nLSTM held-out test (NASA official, {len(y_test)} engines): MAE={lstm_mae:.2f} cycles, R2={lstm_r2:.3f}")

    # --- Honest comparison against the existing tree-based model ---
    tree_mae = None
    if METRICS_PATH.exists():
        existing = json.loads(METRICS_PATH.read_text())
        best_name = existing.get("best_model")
        if best_name and best_name in existing.get("all_models", {}):
            tree_mae = existing["all_models"][best_name]["held_out_test_mae_cycles"]

    lstm_wins = tree_mae is not None and lstm_mae < tree_mae
    if tree_mae is not None:
        pct = round((1 - lstm_mae / tree_mae) * 100, 1)
        verdict = f"LSTM is {pct}% better" if lstm_wins else f"LSTM is {-pct}% WORSE — tree-based model stays live"
        print(f"Tree-based model's existing held-out MAE: {tree_mae} cycles. {verdict}.")
    else:
        print("No existing tree-model metrics found to compare against.")

    # Always save the LSTM model + scaler — even if it doesn't win, it's
    # kept on disk (and its honest numbers recorded) so this comparison is
    # reproducible and the model can be inspected/reused, same "disclose
    # everything, hide nothing" convention as every other training script
    # in this project.
    model.save(LSTM_MODEL_PATH)
    import joblib
    joblib.dump(scaler, LSTM_SCALER_PATH)

    # Merge into the existing model_metrics.json rather than overwrite it —
    # the tree-model comparison table stays intact, this just adds the
    # LSTM as another honestly-reported candidate plus a `live_model`
    # pointer for health_service.py to read.
    existing = json.loads(METRICS_PATH.read_text()) if METRICS_PATH.exists() else {}
    existing.setdefault("all_models", {})
    existing["all_models"]["lstm_deep_learning"] = {
        "held_out_test_mae_cycles": round(lstm_mae, 2),
        "held_out_test_r2": round(lstm_r2, 3),
        "architecture": "LSTM(64)->Dropout->LSTM(32)->Dropout->Dense(16)->Dense(1)",
        "sequence_length": SEQUENCE_LENGTH,
        "epochs_trained": epochs_trained,
        "training_sequences": int(len(X_train)),
    }
    existing["live_model"] = "lstm_deep_learning" if lstm_wins else existing.get("best_model", "hist_gradient_boosting")
    existing["lstm_vs_tree_comparison"] = {
        "lstm_mae_cycles": round(lstm_mae, 2),
        "tree_mae_cycles": tree_mae,
        "lstm_wins": lstm_wins,
    }
    METRICS_PATH.write_text(json.dumps(existing, indent=2))
    print(f"\nSaved LSTM model -> {LSTM_MODEL_PATH}")
    print(f"Saved scaler -> {LSTM_SCALER_PATH}")
    print(f"Updated {METRICS_PATH} — live_model = '{existing['live_model']}'")


if __name__ == "__main__":
    train()
