"""Core integration tests — uses conftest fixtures for proper DB isolation."""
from app.services.stress.stress_engine import StressEngine


def test_health_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in ("healthy", "degraded", "unhealthy")
    assert "database" in payload
    assert "redis" in payload


def test_analyze_endpoint(client):
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


def test_risk_overview_and_stress_scenarios_endpoints(client):
    response = client.get("/api/v1/risk/overview")
    assert response.status_code == 200
    payload = response.json()
    assert "overall_risk" in payload

    response = client.get("/api/v1/stress-test/scenarios")
    assert response.status_code == 200
    payload = response.json()
    assert "scenarios" in payload
    scenario_names = [s["name"] for s in payload["scenarios"]]
    assert "GEOPOLITICAL_SHOCK" in scenario_names


def test_stress_engine():
    engine = StressEngine()
    result = engine.stress_test({
        "total_value": 100_000_000,
        "positions": [
            {"asset_class": "Corporate Loans", "notional": 30_000_000},
            {"asset_class": "Government Bonds", "notional": 20_000_000, "duration": 5.0},
            {"asset_class": "Corporate Bonds", "notional": 15_000_000, "duration": 4.0},
            {"asset_class": "Equities", "notional": 20_000_000},
            {"asset_class": "Derivatives", "notional": 10_000_000},
            {"asset_class": "Cash", "notional": 5_000_000},
        ]
    }, "GEOPOLITICAL_SHOCK")
    assert result["scenario"] == "GEOPOLITICAL_SHOCK"
    assert result["portfolio_before"] > result["portfolio_after"]
