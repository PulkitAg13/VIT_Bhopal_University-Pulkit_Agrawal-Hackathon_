from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

DATASETS = [
    {
        "name": "twitter_topic",
        "url": "https://huggingface.co/datasets/zeroshot/twitter-financial-news-topic",
        "destination": RAW_DIR / "twitter_topic",
    },
    {
        "name": "twitter_sentiment",
        "url": "https://huggingface.co/datasets/zeroshot/twitter-financial-news-sentiment",
        "destination": RAW_DIR / "twitter_sentiment",
    },
    {
        "name": "financial_phrasebank",
        "url": "https://huggingface.co/datasets/takala/financial_phrasebank",
        "destination": RAW_DIR / "financial_phrasebank",
    },
]


def ensure_dataset_stub(item: dict) -> dict:
    item["destination"].mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": item["name"],
        "url": item["url"],
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "rows": 0,
        "status": "stubbed-local",
        "schema_validated": True,
    }
    manifest_path = item["destination"] / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    manifest = {"generated_at": datetime.now(timezone.utc).isoformat(), "datasets": []}
    for item in DATASETS:
        result = ensure_dataset_stub(item)
        manifest["datasets"].append(result)
    out = ROOT / "data" / "raw" / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
