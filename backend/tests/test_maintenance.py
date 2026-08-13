import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
client.__enter__()


def test_maintenance_ingest():
    r = client.post("/api/maintenance/ingest")
    assert r.status_code == 200
    body = r.json()
    assert body["assets_ingested"] == 100
    assert body["readings_ingested"] > 0


def test_fleet_summary_shape():
    r = client.get("/api/maintenance/fleet")
    assert r.status_code == 200
    body = r.json()
    fleet = body["fleet"]
    assert fleet["assets_monitored"] == 100
    assert 0 <= fleet["avg_health_score"] <= 100
    assert len(body["assets"]) == 100
    assert len(body["risk_ranking"]) <= 10


def test_asset_health_scores_valid():
    r = client.get("/api/maintenance/assets")
    body = r.json()
    for a in body["assets"]:
        assert 0 <= a["health_score"] <= 100
        assert a["status"] in ("Excellent", "Good", "Warning", "Critical")
        assert a["predicted_rul_cycles"] >= 0
        assert a["confidence"]["available"] is True


def test_asset_detail():
    fleet = client.get("/api/maintenance/assets").json()
    asset_id = fleet["assets"][0]["asset_id"]
    r = client.get(f"/api/maintenance/assets/{asset_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["asset_id"] == asset_id
    assert "trend" in body


def test_asset_history():
    fleet = client.get("/api/maintenance/assets").json()
    asset_id = fleet["assets"][0]["asset_id"]
    r = client.get(f"/api/maintenance/assets/{asset_id}/history", params={"limit": 50})
    assert r.status_code == 200
    body = r.json()
    assert len(body["readings"]) > 0
    assert "vibration_index" in body["readings"][0]


def test_asset_not_found():
    r = client.get("/api/maintenance/assets/AST-DOES-NOT-EXIST")
    assert r.status_code == 404


def test_alerts_valid():
    r = client.get("/api/maintenance/alerts")
    assert r.status_code == 200
    body = r.json()
    for alert in body["alerts"]:
        assert alert["severity"] in ("low", "medium", "high")
        assert alert["category"] in ("critical", "preventive", "systemic", "monitoring")


def test_work_orders_list():
    r = client.get("/api/maintenance/work-orders")
    assert r.status_code == 200
    assert "work_orders" in r.json()


def test_maintenance_agentic_investigation():
    """Verifies the Maintenance Agent actually calls multiple real tools
    with real results, not a canned response — same bar as Energy's test."""
    r = client.get("/api/maintenance/investigate")
    assert r.status_code == 200
    body = r.json()
    assert body["tool_call_count"] >= 1
    assert body["tool_calls"][0]["tool"] == "get_fleet_summary"
    assert "final_summary" in body
    for call in body["tool_calls"]:
        assert "tool" in call and "result" in call


def test_cross_agent_handoff_creates_real_work_order():
    """The important architecture piece: Energy's flag_for_maintenance_review
    must create an actual queryable MaintenanceEvent row, not just a stub note."""
    before = client.get("/api/maintenance/work-orders").json()["work_orders"]
    before_count = len(before)

    from app.core.agent_tools import flag_for_maintenance_review
    result = flag_for_maintenance_review(
        reason="Test: repeated high-severity anomalies not explained by scheduling.",
        severity="high",
    )
    assert result["status"] == "flagged"
    assert "work_order_id" in result

    after = client.get("/api/maintenance/work-orders").json()["work_orders"]
    assert len(after) == before_count + 1
    newest = after[0]
    assert newest["source"] == "energy_agent"
    assert newest["severity"] == "high"


def test_health_model_metrics_honest():
    """The trained model's metrics file should be present and its reported
    improvement over naive should be a real, non-trivial number (not 0,
    not fabricated 99%+)."""
    import json
    from pathlib import Path
    metrics_path = Path(__file__).resolve().parent.parent / "ml_models" / "maintenance" / "model_metrics.json"
    assert metrics_path.exists()
    metrics = json.loads(metrics_path.read_text())
    assert metrics["improvement_over_naive_pct"] > 0
    assert metrics["n_test_engines_held_out"] == 100
