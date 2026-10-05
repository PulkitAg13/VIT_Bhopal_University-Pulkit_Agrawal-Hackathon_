def test_api_analyze_valid(client):
    response = client.post("/api/v1/analyze", json={
        "text": "Federal Reserve unexpected rate hike dampens equity valuation.",
        "source_name": "Bloomberg",
        "source_type": "rss",
    })
    assert response.status_code == 200
    data = response.json()
    assert "signal_id" in data
    assert "sentiment" in data
    assert "impact" in data


def test_api_analyze_empty_text_error(client):
    response = client.post("/api/v1/analyze", json={
        "text": "",
        "source_name": "Test",
    })
    assert response.status_code in [400, 422]


def test_api_events_list_and_filter(client):
    # Ingest one event first
    client.post("/api/v1/analyze", json={
        "text": "Corporate earnings exceed expectations significantly.",
        "source_name": "CNBC",
        "source_type": "rss",
    })

    # Test list
    response = client.get("/api/v1/events?limit=10")
    assert response.status_code == 200
    events = response.json()
    assert isinstance(events, list)

    # Test filtering by risk level
    response_filt = client.get("/api/v1/events?risk_level=HIGH")
    assert response_filt.status_code == 200


def test_api_portfolio_endpoint(client):
    response = client.get("/api/v1/portfolio")
    assert response.status_code == 200
    data = response.json()
    assert "total_value" in data
    assert "positions" in data
    assert len(data["positions"]) > 0


def test_api_stress_endpoints(client):
    scenarios_resp = client.get("/api/v1/stress-test/scenarios")
    assert scenarios_resp.status_code == 200
    assert "scenarios" in scenarios_resp.json()

    run_resp = client.post("/api/v1/stress-test/run", json={
        "scenario": "GEOPOLITICAL_SHOCK",
    })
    assert run_resp.status_code == 200
    sim = run_resp.json()
    assert "simulation_id" in sim
    assert sim["loss_percentage"] >= 0
