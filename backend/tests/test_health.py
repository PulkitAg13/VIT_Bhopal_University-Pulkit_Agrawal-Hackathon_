"""Test health and readiness endpoints."""


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "FinRisk Intelligence"
    assert data["status"] == "ok"


def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded", "unhealthy")
    assert "database" in data
    assert "redis" in data
    assert "models" in data


def test_readiness_endpoint(client):
    response = client.get("/api/v1/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ready", "degraded", "not_ready")
    assert "database" in data
    assert "redis" in data
