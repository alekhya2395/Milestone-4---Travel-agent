from __future__ import annotations

from fastapi.testclient import TestClient

from travel_agent.web.app import app

CANONICAL = (
    "Plan a 5-day trip to Japan. Tokyo + Kyoto. $3,000 budget. "
    "Love food and temples, hate crowds."
)


def test_health():
    client = TestClient(app)
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_plan_stub():
    client = TestClient(app)
    res = client.post("/api/plan", json={"request": CANONICAL, "stub": True})
    assert res.status_code == 200
    data = res.json()
    assert data["trip_spec"] is not None
    assert data["draft_itinerary"] is not None
    assert "markdown" in data
    assert data["validation_status"] in ("pass", "fail")


def test_plan_empty_rejected():
    client = TestClient(app)
    res = client.post("/api/plan", json={"request": "   ", "stub": True})
    assert res.status_code == 422


def test_static_index():
    client = TestClient(app)
    res = client.get("/")
    assert res.status_code == 200
    assert "Tripzy" in res.text
