"""
Milestone 3 — Security / access-control event dataset builder.

IMPORTANT HONESTY NOTE (read this before citing this module anywhere):
Unlike the Energy, Maintenance, and Occupancy datasets, there is no
practical, license-clear public dataset of real building access-control /
CCTV events available to us. This dataset is FULLY SYNTHETIC — generated
with a realistic statistical structure (business-hours traffic shape, badge
grant/deny rates, per-door risk profiles) and a set of DELIBERATELY INJECTED
anomalies with known ground-truth labels (after-hours access, repeated
denials/possible brute-force, tailgating flags, restricted-zone access by
unauthorized badges).

This lets the Security Agent's anomaly detector be evaluated HONESTLY:
because we know exactly which rows are the injected anomalies, we can
report real precision/recall/F1 for how well an unsupervised detector
(which never sees these labels during training) recovers them — instead of
just asserting the detector "works." This is a standard, legitimate
technique for evaluating anomaly detection when no real labeled incident
data exists — but it is not a substitute for validation against real
security incidents, and that limitation should be stated wherever this
module's results are presented.

REVISION NOTE (accuracy pass): the original `repeated_denial` injection
created a single isolated denied event under that label — a mismatch
between the label's name and its actual shape that made the pattern
undetectable by any feature, since no burst existed for a feature to
find. This revision makes it a genuine burst (2-5 consecutive denied
attempts by the same employee at the same door within ~2 minutes),
matching what "repeated denial" should actually mean and giving the
anomaly detector's time-windowed denial-rate feature something real to
catch.
"""
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

np.random.seed(23)

PROCESSED_DIR = Path(__file__).resolve().parent / "processed"

N_DAYS = 60

ACCESS_POINTS = [
    {"access_point_id": "AP-01", "name": "Main Entrance", "zone_id": "ZN-06", "risk_level": "low"},
    {"access_point_id": "AP-02", "name": "Open Office Floor 1 Door", "zone_id": "ZN-01", "risk_level": "low"},
    {"access_point_id": "AP-03", "name": "Open Office Floor 2 Door", "zone_id": "ZN-02", "risk_level": "low"},
    {"access_point_id": "AP-04", "name": "Server Room Door", "zone_id": "ZN-07", "risk_level": "high"},
    {"access_point_id": "AP-05", "name": "Executive Wing Door", "zone_id": "ZN-08", "risk_level": "medium"},
    {"access_point_id": "AP-06", "name": "Loading Dock", "zone_id": None, "risk_level": "medium"},
    {"access_point_id": "AP-07", "name": "Emergency Exit - East", "zone_id": None, "risk_level": "medium"},
]

N_EMPLOYEES = 220
EMPLOYEE_IDS = [f"EMP-{i:04d}" for i in range(1, N_EMPLOYEES + 1)]
# A handful of badges authorized for the high-risk server room, so
# server-room access by anyone else is itself suspicious.
SERVER_ROOM_AUTHORIZED = set(EMPLOYEE_IDS[:6])


def business_hour_weight(ts: pd.Timestamp) -> float:
    if ts.dayofweek >= 5:
        return 0.05
    hour = ts.hour + ts.minute / 60
    if 8.5 <= hour <= 18.5:
        # Bell-curve-ish peak around mid-morning and a smaller one after lunch.
        return 0.6 + 0.4 * np.exp(-((hour - 9.5) ** 2) / 6) + 0.25 * np.exp(-((hour - 14.5) ** 2) / 8)
    if 6 <= hour < 8.5 or 18.5 < hour <= 21:
        return 0.15
    return 0.02


def build():
    end_anchor = pd.Timestamp(datetime.now()).floor("h")
    start_anchor = end_anchor - timedelta(days=N_DAYS)

    events = []
    event_id = 1

    for ap in ACCESS_POINTS:
        # Simulate arrival times across the window with a non-homogeneous
        # Poisson-ish process weighted by business_hour_weight.
        t = start_anchor
        base_rate_per_min = {"low": 0.9, "medium": 0.25, "high": 0.05}[ap["risk_level"]]
        while t < end_anchor:
            weight = business_hour_weight(t)
            # Expected events in this 5-minute bucket.
            expected = base_rate_per_min * weight * 5
            n_events = np.random.poisson(max(expected, 0.001))
            for _ in range(n_events):
                jitter = timedelta(seconds=np.random.randint(0, 300))
                event_time = t + jitter
                employee_id = np.random.choice(EMPLOYEE_IDS)

                is_anomaly = False
                anomaly_type = None
                access_granted = True

                # --- Injected anomaly patterns (ground truth) ---
                # 1. Server room access by an unauthorized badge.
                if ap["access_point_id"] == "AP-04" and employee_id not in SERVER_ROOM_AUTHORIZED:
                    is_anomaly = True
                    anomaly_type = "unauthorized_restricted_zone_access"
                    access_granted = np.random.random() < 0.3  # mostly denied, occasionally "tailgated" through

                # 2. Rare random after-hours anomaly injection at any door
                # (deliberately independent of the natural low after-hours
                # traffic, so it's a genuine outlier, not just "it was 11pm").
                elif business_hour_weight(event_time) < 0.05 and np.random.random() < 0.04:
                    is_anomaly = True
                    anomaly_type = "after_hours_access"
                    access_granted = np.random.random() < 0.7

                # 3. Genuine repeated-denial BURST (possible brute force /
                # lost badge): the same employee makes several failed
                # attempts at the same door within a couple of minutes.
                # An earlier version of this generator injected only a
                # single isolated denial under this label — a mismatch
                # between the label's name and what it actually represented
                # that made the pattern undetectable by design (no burst
                # existed for any feature to find). Fixed here so the label
                # matches a real, learnable pattern.
                elif np.random.random() < 0.0015:
                    is_anomaly = True
                    anomaly_type = "repeated_denial"
                    access_granted = False
                    burst_employee = employee_id
                    burst_ap = ap
                    burst_start = event_time
                    events.append({
                        "event_id": f"EVT-{event_id:07d}", "access_point_id": burst_ap["access_point_id"],
                        "access_point_name": burst_ap["name"], "zone_id": burst_ap["zone_id"],
                        "risk_level": burst_ap["risk_level"], "employee_id": burst_employee,
                        "timestamp": burst_start, "access_granted": False,
                        "is_anomaly": True, "anomaly_type": "repeated_denial",
                    })
                    event_id += 1
                    burst_len = np.random.randint(2, 5)  # 2-4 MORE denied attempts follow
                    for k in range(burst_len):
                        retry_time = burst_start + timedelta(seconds=int(np.random.randint(20, 90) * (k + 1)))
                        events.append({
                            "event_id": f"EVT-{event_id:07d}", "access_point_id": burst_ap["access_point_id"],
                            "access_point_name": burst_ap["name"], "zone_id": burst_ap["zone_id"],
                            "risk_level": burst_ap["risk_level"], "employee_id": burst_employee,
                            "timestamp": retry_time, "access_granted": False,
                            "is_anomaly": True, "anomaly_type": "repeated_denial",
                        })
                        event_id += 1
                    continue  # this event + its burst are already appended above

                else:
                    access_granted = np.random.random() < 0.985  # ordinary, occasional benign badge misread

                events.append({
                    "event_id": f"EVT-{event_id:07d}",
                    "access_point_id": ap["access_point_id"],
                    "access_point_name": ap["name"],
                    "zone_id": ap["zone_id"],
                    "risk_level": ap["risk_level"],
                    "employee_id": employee_id,
                    "timestamp": event_time,
                    "access_granted": bool(access_granted),
                    "is_anomaly": bool(is_anomaly),
                    "anomaly_type": anomaly_type,
                })
                event_id += 1
            t += timedelta(minutes=5)

    df = pd.DataFrame(events).sort_values("timestamp").reset_index(drop=True)
    PROCESSED_DIR.mkdir(exist_ok=True)
    df.to_csv(PROCESSED_DIR / "security_access_events.csv", index=False)

    ap_df = pd.DataFrame(ACCESS_POINTS)
    ap_df.to_csv(PROCESSED_DIR / "security_access_points.csv", index=False)

    print(f"Rows: {len(df)}  Access points: {len(ACCESS_POINTS)}")
    print(f"Injected anomalies: {df['is_anomaly'].sum()} ({100*df['is_anomaly'].mean():.2f}% of events)")
    print(df["anomaly_type"].value_counts(dropna=True))
    return df


if __name__ == "__main__":
    build()
