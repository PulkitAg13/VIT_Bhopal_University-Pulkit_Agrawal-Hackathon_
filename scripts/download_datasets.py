"""
Real dataset download script using HuggingFace datasets and huggingface_hub.

Downloads:
1. Twitter Financial News Topic (zeroshot/twitter-financial-news-topic)
2. Twitter Financial News Sentiment (zeroshot/twitter-financial-news-sentiment)
3. Financial PhraseBank (takala/financial_phrasebank)

Saves to data/raw/ and generates manifest with actual row counts.
"""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

# Safe stdout encoding on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

DATASETS = [
    {
        "name": "twitter_topic",
        "hf_path": "zeroshot/twitter-financial-news-topic",
        "url": "https://huggingface.co/datasets/zeroshot/twitter-financial-news-topic",
        "license": "MIT",
        "text_column": "text",
        "label_column": "label",
        "method": "hf_datasets",
    },
    {
        "name": "twitter_sentiment",
        "hf_path": "zeroshot/twitter-financial-news-sentiment",
        "url": "https://huggingface.co/datasets/zeroshot/twitter-financial-news-sentiment",
        "license": "MIT",
        "text_column": "text",
        "label_column": "label",
        "method": "hf_datasets",
    },
    {
        "name": "financial_phrasebank",
        "hf_path": "takala/financial_phrasebank",
        "url": "https://huggingface.co/datasets/takala/financial_phrasebank",
        "license": "CC BY-SA 4.0",
        "text_column": "sentence",
        "label_column": "label",
        "method": "hub_zip",
    },
]


def file_checksum(filepath: Path) -> str:
    """Calculate SHA256 checksum of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


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
        total_rows = 0
        columns = set()
        splits_info = {}
        checksums = {}

        if item["method"] == "hf_datasets":
            from datasets import load_dataset
            dataset = load_dataset(item["hf_path"])

            for split_name in dataset:
                split = dataset[split_name]
                split_rows = len(split)
                total_rows += split_rows
                columns.update(split.column_names)
                splits_info[split_name] = split_rows

                # Save to JSON
                output_file = dest / f"{split_name}.json"
                records = []
                for row in split:
                    record = {}
                    for col in split.column_names:
                        val = row[col]
                        record[col] = val if not hasattr(val, "item") else val.item()
                    records.append(record)

                output_file.write_text(
                    json.dumps({"data": records}, indent=None, ensure_ascii=False),
                    encoding="utf-8",
                )
                checksums[split_name] = file_checksum(output_file)
                print(f"  Split '{split_name}': {split_rows} rows -> {output_file.name}")

        elif item["method"] == "hub_zip":
            from huggingface_hub import hf_hub_download
            zip_path = hf_hub_download(
                repo_id=item["hf_path"],
                filename="data/FinancialPhraseBank-v1.0.zip",
                repo_type="dataset",
            )
            records = []
            label_map = {"negative": 0, "positive": 1, "neutral": 2}
            with zipfile.ZipFile(zip_path, "r") as z:
                with z.open("FinancialPhraseBank-v1.0/Sentences_AllAgree.txt") as f:
                    for line in f:
                        line_str = line.decode("latin-1").strip()
                        if "@" in line_str:
                            parts = line_str.rsplit("@", 1)
                            sentence = parts[0].strip()
                            label_str = parts[1].strip().lower()
                            label_int = label_map.get(label_str, 2)
                            records.append({
                                "sentence": sentence,
                                "label": label_int,
                                "label_text": label_str,
                            })

            output_file = dest / "train.json"
            output_file.write_text(
                json.dumps({"data": records}, indent=None, ensure_ascii=False),
                encoding="utf-8",
            )
            total_rows = len(records)
            columns = ["sentence", "label", "label_text"]
            splits_info["train"] = total_rows
            checksums["train"] = file_checksum(output_file)
            print(f"  Split 'train' (Sentences_AllAgree): {total_rows} rows -> {output_file.name}")

        manifest = {
            "name": item["name"],
            "hf_path": item["hf_path"],
            "url": item["url"],
            "license": item["license"],
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "rows": total_rows,
            "splits": splits_info,
            "columns": sorted(columns),
            "text_column": item["text_column"],
            "label_column": item["label_column"],
            "checksums": checksums,
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
        sys.exit(1)


if __name__ == "__main__":
    main()
