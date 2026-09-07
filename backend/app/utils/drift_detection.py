"""
Shared "does this data still look like what the model was trained on"
check — used by every domain's service module (forecast_service.py,
health_service.py, occupancy_service.py, security_service.py,
cost_service.py) so there's one implementation instead of five near-copies
that could quietly drift apart.

Background: uploading a differently-shaped/differently-scaled dataset
(see backend/app/utils/csv_upload.py) was already verified to ingest and
produce a prediction without crashing — but the accuracy/confidence
numbers shown alongside every prediction come from `model_metrics.json`,
computed once at TRAINING time, and never re-evaluated against whatever
is actually loaded right now. Without a drift signal, a wildly different
dataset would still show the original "R²=0.99, high confidence" as if
nothing had changed. This module is a proxy, not a re-measurement: it
can't tell you the model's ACTUAL accuracy on new data (there's no
ground-truth future value to check a live prediction against), only
whether the new data's basic shape resembles the data that accuracy
number was earned on.
"""


def compute_drift(current_means: dict[str, float], training_distribution: dict[str, dict]) -> dict:
    """
    current_means: {column_name: current_mean_value} for whatever columns
        are available right now (missing ones are simply skipped).
    training_distribution: {column_name: {"mean": ..., "std": ...}} as
        saved by a training script at training time.

    Returns a dict with `drift_detected`, a severity `level`
    ("none"/"medium"/"high"), the specific `flags` that tripped it, and a
    human-readable `note` naming the first (usually most informative)
    flagged column — same shape regardless of which domain calls this.
    """
    flags = []
    for col, current_mean in current_means.items():
        stats = training_distribution.get(col)
        if not stats or current_mean is None:
            continue
        train_mean, train_std = stats["mean"], stats["std"]
        if train_std <= 0:
            continue
        z = abs(current_mean - train_mean) / train_std
        if z >= 2:
            flags.append({
                "column": col, "z_score": round(z, 2),
                "current_mean": round(current_mean, 2), "training_mean": train_mean,
            })

    if not flags:
        return {"available": True, "drift_detected": False, "level": "none", "flags": []}

    max_z = max(f["z_score"] for f in flags)
    level = "high" if max_z >= 4 else "medium"
    lead = flags[0]
    return {
        "available": True,
        "drift_detected": True,
        "level": level,
        "flags": flags,
        "note": (
            f"The current data's average {lead['column'].replace('_', ' ')} differs substantially from "
            f"the dataset this model was trained on ({lead['current_mean']} vs {lead['training_mean']} "
            f"expected) — the accuracy/confidence numbers shown were measured on the ORIGINAL training "
            f"data and may not hold for this dataset."
        ),
    }
