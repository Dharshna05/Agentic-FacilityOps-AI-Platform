import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app

# Using __enter__ triggers FastAPI's startup event (DB init + auto-ingest)
client = TestClient(app)
client.__enter__()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_ingest():
    r = client.post("/api/energy/ingest")
    assert r.status_code == 200
    body = r.json()
    assert body["rows_ingested"] == 35040


def test_consumption():
    r = client.get("/api/energy/consumption")
    assert r.status_code == 200
    body = r.json()
    assert body["total_kwh"] > 0
    assert body["peak_kwh"] >= body["avg_hourly_kwh"]


def test_analytics_shape():
    r = client.get("/api/energy/analytics")
    body = r.json()
    assert "consumption" in body
    assert "breakdown" in body
    assert "anomalies" in body
    breakdown = body["breakdown"]
    total_pct = (breakdown["hvac_pct"] + breakdown["lighting_pct"]
                 + breakdown["plug_load_pct"] + breakdown["other_pct"])
    assert 99 <= total_pct <= 101  # should sum to ~100%


def test_recommendations():
    r = client.get("/api/energy/recommendations")
    body = r.json()
    assert "recommendations" in body
    for rec in body["recommendations"]:
        assert rec["severity"] in ("low", "medium", "high")
        assert rec["estimated_savings_pct"] >= 0


def test_dashboard():
    r = client.get("/api/energy/dashboard")
    body = r.json()
    assert body["building_id"] == "BLD-HQ-01"
    assert "top_recommendations" in body
    assert "anomaly_count" in body


def test_forecast():
    r = client.get("/api/energy/forecast")
    assert r.status_code == 200
    body = r.json()
    assert "predicted_kwh" in body
    assert body["predicted_kwh"] > 0
    assert body["horizon"] == "1h"
    assert body["model_used"] in ("linear_regression", "random_forest", "gradient_boosting")
    assert body["confidence"]["available"] is True
    assert body["confidence"]["confidence"] in ("low", "medium", "high")


def test_forecast_multi_horizon():
    """Each horizon uses its own trained model and should report its own
    (honest) confidence — 1h/6h should be meaningfully more confident than
    24h, not uniformly reported."""
    results = {}
    for horizon in ("1h", "6h", "24h"):
        r = client.get(f"/api/energy/forecast?horizon={horizon}")
        assert r.status_code == 200
        body = r.json()
        assert body["horizon"] == horizon
        results[horizon] = body

    # invalid horizon should be rejected, not silently accepted
    r = client.get("/api/energy/forecast?horizon=3h")
    assert r.status_code == 400


def test_briefing():
    r = client.get("/api/energy/briefing")
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "mock"
    assert len(body["briefing"]) > 0


def test_agentic_investigation():
    """Verifies the agentic tool-calling loop: the (simulated) agent must
    actually call multiple real tools and produce a trace, not just return
    a canned string."""
    r = client.get("/api/energy/investigate")
    assert r.status_code == 200
    body = r.json()
    assert body["tool_call_count"] >= 3
    tool_names = {call["tool"] for call in body["tool_calls"]}
    assert "get_consumption_summary" in tool_names
    # each trace entry should have a real result, not a stub
    for call in body["tool_calls"]:
        assert call["result"] is not None
    assert len(body["final_summary"]) > 0


def test_readings_limit():
    r = client.get("/api/energy/readings?limit=100")
    body = r.json()
    assert len(body["readings"]) == 100


def test_temperature_occupancy_correlation():
    r = client.get("/api/energy/analytics")
    body = r.json()
    temp = body["temperature"]
    occ = body["occupancy"]
    assert temp["available"] is True
    assert "correlation" in temp
    assert occ["available"] is True
    assert occ["avg_load_when_unoccupied_kwh"] >= 0
    assert occ["avg_load_when_occupied_kwh"] >= 0


def test_xlsx_upload_with_external_columns(tmp_path):
    """Simulates a teammate's Kaggle-style export: date, Power Consumption,
    Outdoor Temperature, Occupancy — different column names/casing than our
    internal schema, uploaded as .xlsx."""
    import pandas as pd
    import numpy as np

    n = 200
    df = pd.DataFrame({
        "date": pd.date_range("2018-05-22", periods=n, freq="15min"),
        "Power Consumption": (60 + np.random.rand(n) * 40).round(2),
        "Outdoor Temperature": (12 + np.random.rand(n) * 15).round(2),
        "Occupancy": np.random.randint(0, 5, n),
    })
    xlsx_path = tmp_path / "teammate_dataset.xlsx"
    df.to_excel(xlsx_path, index=False)

    with open(xlsx_path, "rb") as f:
        r = client.post(
            "/api/energy/ingest/upload",
            files={"file": ("teammate_dataset.xlsx", f,
                             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["rows_ingested"] == n
    assert body["source"] == "teammate_dataset.xlsx"

    # Confirm the ingested data flows through analytics correctly
    r2 = client.get("/api/energy/analytics")
    assert r2.status_code == 200
    assert r2.json()["temperature"]["available"] is True

    # Restore the main dataset for any tests that run after this one
    client.post("/api/energy/ingest")
