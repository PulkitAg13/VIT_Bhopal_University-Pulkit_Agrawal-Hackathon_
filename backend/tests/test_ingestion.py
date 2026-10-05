import pytest
from app.services.ingestion.sources import get_source, RSSNewsSource, DatasetReplaySource, DemoSource


def test_get_source_factory():
    rss = get_source("rss", ticker="AAPL")
    assert isinstance(rss, RSSNewsSource)

    dataset = get_source("dataset", dataset_name="twitter_sentiment")
    assert isinstance(dataset, DatasetReplaySource)

    demo = get_source("demo")
    assert isinstance(demo, DemoSource)

    with pytest.raises(ValueError, match="Unsupported source type"):
        get_source("invalid_source_type_123")


def test_demo_source_fetch():
    demo = DemoSource()
    items = demo.fetch(max_items=3)
    assert len(items) <= 3
    assert len(items) > 0
    assert items[0].source_type == "demo"
    assert len(items[0].text) > 10


def test_dataset_replay_fetch_real_data():
    source = DatasetReplaySource("twitter_sentiment")
    items = source.fetch(max_items=5)
    assert len(items) > 0
    assert items[0].source_type == "dataset"
    assert "twitter" in items[0].source_url.lower()


def test_dataset_replay_missing_raises():
    source = DatasetReplaySource("nonexistent_dataset_abc_xyz")
    with pytest.raises(FileNotFoundError):
        source.fetch(max_items=5)


def test_api_ingest_demo(client):
    response = client.post("/api/v1/ingest", json={
        "source": "demo",
        "max_items": 2,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["ingested"] > 0
    assert len(data["signals"]) > 0


def test_api_ingest_missing_dataset_404(client):
    response = client.post("/api/v1/ingest", json={
        "source": "dataset",
        "dataset_name": "unknown_dataset_404",
        "max_items": 2,
    })
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_api_ingest_invalid_source_400(client):
    response = client.post("/api/v1/ingest", json={
        "source": "completely_invalid_source",
        "max_items": 2,
    })
    assert response.status_code == 400
