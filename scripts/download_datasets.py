"""
Real dataset download script using HuggingFace datasets library.

Downloads:
1. Twitter Financial News Topic (zeroshot/twitter-financial-news-topic)
2. Twitter Financial News Sentiment (zeroshot/twitter-financial-news-sentiment)
3. Financial PhraseBank (takala/financial_phrasebank)

Saves to data/raw/ and generates manifest with actual row counts.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

DATASETS = [
    {
        "name": "twitter_topic",
        "hf_path": "zeroshot/twitter-financial-news-topic",
        "url": "https://huggingface.co/datasets/zeroshot/twitter-financial-news-topic",
        "text_column": "text",
        "label_column": "label",
    },
    {
        "name": "twitter_sentiment",
        "hf_path": "zeroshot/twitter-financial-news-sentiment",
        "url": "https://huggingface.co/datasets/zeroshot/twitter-financial-news-sentiment",
        "text_column": "text",
        "label_column": "label",
    },
    {
        "name": "financial_phrasebank",
        "hf_path": "takala/financial_phrasebank",
        "hf_config": "sentences_allagree",
        "url": "https://huggingface.co/datasets/takala/financial_phrasebank",
        "text_column": "sentence",
        "label_column": "label",
    },
]


def download_dataset(item: dict) -> dict:
    """Download a single dataset from HuggingFace."""
    dest = RAW_DIR / item["name"]
    dest.mkdir(parents=True, exist_ok=True)

    manifest_path = dest / "manifest.json"

    # Check if already downloaded
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            if existing.get("status") == "downloaded" and existing.get("rows", 0) > 0:
                print(f"  Already downloaded: {item['name']} ({existing['rows']} rows)")
                return existing
        except Exception:
            pass

    print(f"\nDownloading {item['name']}...")
    print(f"  Source: {item['url']}")

    try:
        from datasets import load_dataset

        kwargs = {"path": item["hf_path"]}
        if item.get("hf_config"):
            kwargs["name"] = item["hf_config"]

        dataset = load_dataset(**kwargs)

        # Get all splits
        total_rows = 0
        columns = set()
        splits_info = {}

        for split_name in dataset:
            split = dataset[split_name]
            split_rows = len(split)
            total_rows += split_rows
            columns.update(split.column_names)
            splits_info[split_name] = split_rows

            # Save to JSON
            output_file = dest / f"{split_name}.json"
            records = []
            for i, row in enumerate(split):
                record = {}
                for col in split.column_names:
                    val = row[col]
                    record[col] = val if not hasattr(val, 'item') else val.item()
                records.append(record)

            output_file.write_text(
                json.dumps({"data": records}, indent=None, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"  Split '{split_name}': {split_rows} rows → {output_file.name}")

        manifest = {
            "name": item["name"],
            "hf_path": item["hf_path"],
            "url": item["url"],
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "rows": total_rows,
            "splits": splits_info,
            "columns": sorted(columns),
            "text_column": item["text_column"],
            "label_column": item["label_column"],
            "status": "downloaded",
            "schema_validated": True,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        print(f"  Total rows: {total_rows}")
        print(f"  Columns: {', '.join(sorted(columns))}")
        return manifest

    except Exception as exc:
        print(f"  ERROR downloading {item['name']}: {exc}")
        error_manifest = {
            "name": item["name"],
            "url": item["url"],
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "rows": 0,
            "status": f"error: {str(exc)}",
            "schema_validated": False,
        }
        manifest_path.write_text(json.dumps(error_manifest, indent=2), encoding="utf-8")
        return error_manifest


def main() -> None:
    print("=" * 60)
    print("FinRisk Intelligence — Dataset Download")
    print("=" * 60)

    overall_manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "datasets": [],
    }

    success_count = 0
    for item in DATASETS:
        result = download_dataset(item)
        overall_manifest["datasets"].append(result)
        if result.get("status") == "downloaded":
            success_count += 1

    # Save overall manifest
    manifest_path = RAW_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(overall_manifest, indent=2), encoding="utf-8")

    print("\n" + "=" * 60)
    print(f"Download complete: {success_count}/{len(DATASETS)} datasets")
    print(f"Manifest: {manifest_path}")

    total_rows = sum(d.get("rows", 0) for d in overall_manifest["datasets"])
    print(f"Total rows: {total_rows}")
    print("=" * 60)

    if success_count < len(DATASETS):
        print("\nWARNING: Some datasets failed to download.")
        print("Run 'pip install datasets' if not installed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
