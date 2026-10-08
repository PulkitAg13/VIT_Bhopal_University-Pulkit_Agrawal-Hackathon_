"""
Data ingestion sources — Real RSS fetching and dataset replay.

Source 1: Yahoo Finance RSS — live financial news
Source 2: Dataset Replay — replays downloaded HuggingFace datasets
"""
from __future__ import annotations

import json
import logging
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("finrisk.ingestion")

_DATA_DIR = Path(__file__).resolve().parents[4] / "data"


class IngestedItem:
    """Represents an ingested text item with metadata."""
    def __init__(
        self,
        text: str,
        source_name: str,
        source_type: str,
        source_url: Optional[str] = None,
        published_at: Optional[datetime] = None,
        retrieved_at: Optional[datetime] = None,
        ticker: Optional[str] = None,
    ):
        self.text = text
        self.source_name = source_name
        self.source_type = source_type
        self.source_url = source_url
        self.published_at = published_at
        self.retrieved_at = retrieved_at or datetime.now(timezone.utc)
        self.ticker = ticker


class RSSNewsSource:
    """Fetch real RSS from Yahoo Finance."""

    RSS_URL_TEMPLATE = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"

    def __init__(self, ticker: str = "AAPL") -> None:
        self.ticker = ticker.upper()
        self.name = f"Yahoo Finance RSS ({self.ticker})"
        self.source_type = "rss"

    def fetch(self, max_items: int = 10) -> List[IngestedItem]:
        """Fetch real RSS headlines from Yahoo Finance."""
        url = self.RSS_URL_TEMPLATE.format(ticker=self.ticker)
        items: List[IngestedItem] = []

        try:
            import feedparser
            feed = feedparser.parse(url)

            if not feed.entries:
                logger.warning("No RSS entries for %s from %s", self.ticker, url)
                return items

            for entry in feed.entries[:max_items]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                link = entry.get("link", "")
                published = entry.get("published", "")

                text = f"{title}. {summary}" if summary and summary != title else title
                if not text.strip():
                    continue

                pub_dt = None
                if published:
                    try:
                        import email.utils
                        parsed = email.utils.parsedate_to_datetime(published)
                        pub_dt = parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
                    except Exception:
                        pass

                items.append(IngestedItem(
                    text=text.strip(),
                    source_name=self.name,
                    source_type="rss",
                    source_url=link,
                    published_at=pub_dt,
                    ticker=self.ticker,
                ))

            logger.info("RSS fetched %d items for %s", len(items), self.ticker)

        except ImportError:
            logger.error("feedparser not installed")
        except Exception as exc:
            logger.error("RSS fetch error for %s: %s", self.ticker, exc)

        return items


class DatasetReplaySource:
    """Replay items from downloaded HuggingFace datasets."""

    def __init__(self, dataset_name: str = "twitter_sentiment") -> None:
        self.dataset_name = dataset_name
        self.name = f"Dataset Replay ({dataset_name})"
        self.source_type = "dataset"

    def fetch(self, max_items: int = 10, shuffle: bool = True) -> List[IngestedItem]:
        """Load texts from downloaded dataset files."""
        items: List[IngestedItem] = []

        # Try loading from parquet/csv/json in data/raw/{dataset_name}/
        dataset_dir = _DATA_DIR / "raw" / self.dataset_name
        if not dataset_dir.exists():
            raise FileNotFoundError(
                f"Dataset '{self.dataset_name}' not found at {dataset_dir}. "
                f"Run 'python scripts/download_datasets.py' to download real HuggingFace datasets."
            )

        texts = []

        # Try CSV
        for csv_file in dataset_dir.glob("*.csv"):
            try:
                import csv
                with open(csv_file, "r", encoding="utf-8") as fh:
                    reader = csv.DictReader(fh)
                    for row in reader:
                        text = row.get("text") or row.get("sentence") or row.get("title", "")
                        if text and len(text.strip()) > 20:
                            texts.append(text.strip())
            except Exception as exc:
                logger.warning("CSV read error: %s", exc)

        # Try JSON
        for json_file in dataset_dir.glob("*.json"):
            if json_file.name == "manifest.json":
                continue
            try:
                with open(json_file, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                records = data if isinstance(data, list) else data.get("data", data.get("rows", []))
                for record in records:
                    if isinstance(record, dict):
                        text = record.get("text") or record.get("sentence", "")
                    else:
                        text = str(record)
                    if text and len(text.strip()) > 20:
                        texts.append(text.strip())
            except Exception as exc:
                logger.warning("JSON read error: %s", exc)

        # Try JSONL
        for jsonl_file in dataset_dir.glob("*.jsonl"):
            try:
                with open(jsonl_file, "r", encoding="utf-8") as fh:
                    for line in fh:
                        record = json.loads(line)
                        text = record.get("text") or record.get("sentence", "")
                        if text and len(text.strip()) > 20:
                            texts.append(text.strip())
            except Exception as exc:
                logger.warning("JSONL read error: %s", exc)

        if not texts:
            raise FileNotFoundError(
                f"No records found in dataset '{self.dataset_name}' at {dataset_dir}. "
                f"Run 'python scripts/download_datasets.py' to download real datasets."
            )

        if shuffle:
            random.shuffle(texts)

        for text in texts[:max_items]:
            items.append(IngestedItem(
                text=text,
                source_name=self.name,
                source_type="dataset",
                source_url=f"https://huggingface.co/datasets/{self.dataset_name}",
            ))

        logger.info("Dataset replay: %d items from %s (total available: %d)",
                    len(items), self.dataset_name, len(texts))
        return items


class DemoSource:
    """Provide synthetic demo events for demonstration."""

    DEMO_EVENTS = [
        {
            "text": "Escalating geopolitical tensions disrupt critical energy supply routes, raising concerns over global inflation and corporate input costs.",
            "source_name": "Synthetic Demo Dataset",
            "source_type": "demo",
        },
        {
            "text": "Federal Reserve signals aggressive rate increases as inflation remains stubbornly above target, banks reassess credit risk exposure across portfolios.",
            "source_name": "Synthetic Demo Dataset",
            "source_type": "demo",
        },
        {
            "text": "Major technology company faces supply chain disruption after shipping delays worsen at critical Asian manufacturing facilities.",
            "source_name": "Synthetic Demo Dataset",
            "source_type": "demo",
        },
        {
            "text": "Credit rating agency downgrades several major financial institutions citing deteriorating asset quality and rising non-performing loan ratios.",
            "source_name": "Synthetic Demo Dataset",
            "source_type": "demo",
        },
        {
            "text": "Strong quarterly earnings from semiconductor sector drive market rally as AI demand continues to accelerate beyond analyst expectations.",
            "source_name": "Synthetic Demo Dataset",
            "source_type": "demo",
        },
    ]

    def __init__(self) -> None:
        self.name = "Synthetic Demo Dataset"
        self.source_type = "demo"

    def fetch(self, max_items: int = 5) -> List[IngestedItem]:
        items = []
        for evt in self.DEMO_EVENTS[:max_items]:
            items.append(IngestedItem(
                text=evt["text"],
                source_name=evt["source_name"],
                source_type=evt["source_type"],
            ))
        return items


def get_source(source_type: str, ticker: str = "AAPL", dataset_name: str = "twitter_sentiment"):
    """Factory to get the right source."""
    s_type = source_type.lower() if source_type else "demo"
    if s_type in ("rss", "yahoo_rss", "live_news"):
        return RSSNewsSource(ticker)
    elif s_type in ("dataset", "huggingface", "dataset_replay"):
        return DatasetReplaySource(dataset_name)
    elif s_type == "demo":
        return DemoSource()
    else:
        raise ValueError(
            f"Unsupported source type: '{source_type}'. "
            f"Supported sources: 'rss' (Yahoo Finance), 'dataset' (HuggingFace replay), 'demo' (deterministic scenarios)."
        )

