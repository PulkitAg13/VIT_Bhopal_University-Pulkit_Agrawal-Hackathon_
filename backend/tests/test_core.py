from fastapi.testclient import TestClient

from app.main import app
from app.services.stress.stress_engine import StressEngine

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_endpoint():
    response = client.post("/api/v1/analyze", json={
        "text": "Escalating geopolitical tensions disrupt critical energy supply routes, raising concerns over global inflation and corporate input costs.",
        "source_name": "demo",
        "source_type": "rss",
    })
    assert response.status_code == 200
    payload = response.json()
    assert "sentiment" in payload
    assert "impact" in payload
    assert "event" in payload
    assert payload["impact"]["score"] >= 1


def test_stress_engine():
    engine = StressEngine()
    result = engine.stress_test({
        "total_value": 100_000_000,
        "positions": [
            {"asset_class": "Corporate Loans", "value": 30_000_000, "exposure": 0.8},
            {"asset_class": "Government Bonds", "value": 20_000_000, "exposure": 0.4},
            {"asset_class": "Corporate Bonds", "value": 15_000_000, "exposure": 0.7},
            {"asset_class": "Equities", "value": 20_000_000, "exposure": 0.9},
            {"asset_class": "Derivatives", "value": 10_000_000, "exposure": 0.8},
            {"asset_class": "Cash", "value": 5_000_000, "exposure": 0.2},
        ]
    }, "GEOPOLITICAL_SHOCK")
    assert result["scenario"] == "GEOPOLITICAL_SHOCK"
    assert result["portfolio_before"] > result["portfolio_after"]
