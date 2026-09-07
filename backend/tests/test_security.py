import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
client.__enter__()


def test_security_ingest():
    r = client.post("/api/security/ingest")
    assert r.status_code == 200
    body = r.json()
    assert body["access_points_ingested"] == 7
    assert body["events_ingested"] > 0


def test_building_summary_shape():
    r = client.get("/api/security/building")
    assert r.status_code == 200
    body = r.json()
    building = body["building"]
    assert building["access_points_monitored"] == 7
    assert building["events_last_24h"] >= 0
    assert body["model_confidence"]["available"] is True
    # Honest unsupervised-detector metrics should be present, not omitted.
    assert body["model_confidence"]["precision"] is not None
    assert body["model_confidence"]["recall"] is not None


def test_access_points_listed():
    r = client.get("/api/security/access-points")
    body = r.json()
    assert len(body["access_points"]) == 7
    risk_levels = {a["risk_level"] for a in body["access_points"]}
    assert risk_levels <= {"low", "medium", "high"}


def test_events_endpoint_excludes_ground_truth_columns():
    """Ground-truth anomaly labels exist in the DB for offline model
    evaluation only — the live API must never leak them, or the "detector"
    would just be reading the answer key."""
    r = client.get("/api/security/events", params={"limit": 20})
    body = r.json()
    assert len(body["events"]) > 0
    for ev in body["events"]:
        assert "is_anomaly_ground_truth" not in ev
        assert "anomaly_type_ground_truth" not in ev


def test_flagged_events_have_anomaly_scores():
    r = client.get("/api/security/building").json()
    for ev in r["flagged_events"]:
        assert 0 <= ev["anomaly_score"]
        assert ev["access_point_id"]


def test_alerts_created_from_high_confidence_flags():
    r = client.get("/api/security/alerts").json()
    for alert in r["alerts"]:
        assert alert["severity"] in ("low", "medium", "high")
        assert alert["source"] in ("security_agent", "occupancy_agent")


def test_investigate_runs_and_returns_trace():
    r = client.get("/api/security/investigate")
    assert r.status_code == 200
    body = r.json()
    assert "final_summary" in body
    assert isinstance(body["tool_calls"], list)


def test_supervised_reference_model_disclosed_and_not_live():
    """Accuracy-pass addition: a third, supervised RandomForest is
    reported as an honest reference point only — never claimed as the
    live scorer."""
    r = client.get("/api/security/building")
    body = r.json()
    ref = body["supervised_reference_confidence"]
    assert ref["available"] is True
    assert "random_forest" in ref["model_used"]
    assert "not" in ref["note"].lower() and "live" in ref["note"].lower()
    # Isolation Forest F1 should be a real, materially-improved number
    # after the accuracy pass (feature engineering + repeated_denial
    # burst fix), not the earlier weak baseline.
    assert body["model_confidence"]["f1"] > 0.6


def test_security_data_drift_quiet_on_original_dataset():
    client.post("/api/security/ingest")
    r = client.get("/api/security/building")
    assert r.json()["data_drift"]["drift_detected"] is False
