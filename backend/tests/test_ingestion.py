"""Test ingestion sources and API endpoints."""
import pytest
from pathlib import Path
from app.services.ingestion.sources import get_source, RSSNewsSource, DatasetReplaySource, DemoSource

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


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


@pytest.mark.skipif(
    not (_DATA_DIR / "raw" / "twitter_sentiment").exists(),
    reason="Dataset not downloaded — run scripts/download_datasets.py first",
)
def test_dataset_replay_fetch_real_data():
    DatasetReplaySource.reset_cursor("twitter_sentiment")
    source = DatasetReplaySource("twitter_sentiment")
    items = source.fetch(max_items=5)
    assert len(items) == 5
    assert items[0].source_type == "dataset"
    assert "huggingface" in items[0].source_url.lower()
    assert "#record-0" in items[0].source_url
    assert "#record-4" in items[4].source_url


@pytest.mark.skipif(
    not (_DATA_DIR / "raw" / "twitter_sentiment").exists(),
    reason="Dataset not downloaded — run scripts/download_datasets.py first",
)
def test_dataset_replay_sequential_progression():
    DatasetReplaySource.reset_cursor("twitter_sentiment")
    source = DatasetReplaySource("twitter_sentiment")

    batch1 = source.fetch(max_items=3)
    batch2 = source.fetch(max_items=3)

    assert len(batch1) == 3
    assert len(batch2) == 3

    # Consecutive batches contain distinct sequential records
    urls1 = [item.source_url for item in batch1]
    urls2 = [item.source_url for item in batch2]
    assert set(urls1).isdisjoint(set(urls2))
    assert urls1 == [
        "https://huggingface.co/datasets/twitter_sentiment#record-0",
        "https://huggingface.co/datasets/twitter_sentiment#record-1",
        "https://huggingface.co/datasets/twitter_sentiment#record-2",
    ]
    assert urls2 == [
        "https://huggingface.co/datasets/twitter_sentiment#record-3",
        "https://huggingface.co/datasets/twitter_sentiment#record-4",
        "https://huggingface.co/datasets/twitter_sentiment#record-5",
    ]


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
    assert "new_count" in data
    assert "already_processed" in data
    assert data["new_count"] + data["already_processed"] == data["ingested"]


def test_api_ingest_duplicate_counts(client):
    # Ingest demo item
    res1 = client.post("/api/v1/ingest", json={"source": "demo", "max_items": 1})
    assert res1.status_code == 200
    # Ingest again - identical item must be counted as already_processed
    res2 = client.post("/api/v1/ingest", json={"source": "demo", "max_items": 1})
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["already_processed"] == 1
    assert data2["new_count"] == 0


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
