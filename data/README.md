# FinRisk Intelligence — Data Directory

## Overview

This directory contains datasets used by the FinRisk Intelligence platform.

## Datasets

All datasets are downloaded from [HuggingFace](https://huggingface.co/) using `scripts/download_datasets.py`.

### 1. Twitter Financial News Topic
- **Source:** [zeroshot/twitter-financial-news-topic](https://huggingface.co/datasets/zeroshot/twitter-financial-news-topic)
- **License:** MIT
- **Purpose:** Financial news classification into topic categories
- **Columns:** `text`, `label`
- **Location:** `data/raw/twitter_topic/`

### 2. Twitter Financial News Sentiment
- **Source:** [zeroshot/twitter-financial-news-sentiment](https://huggingface.co/datasets/zeroshot/twitter-financial-news-sentiment)
- **License:** MIT
- **Purpose:** Financial sentiment analysis training and evaluation data
- **Columns:** `text`, `label`
- **Location:** `data/raw/twitter_sentiment/`

### 3. Financial PhraseBank
- **Source:** [takala/financial_phrasebank](https://huggingface.co/datasets/takala/financial_phrasebank)
- **License:** CC BY-NC-SA 3.0
- **Purpose:** Sentiment analysis of financial news sentences
- **Config:** `sentences_allagree` (sentences with 100% annotator agreement)
- **Columns:** `sentence`, `label`
- **Location:** `data/raw/financial_phrasebank/`

## Models Used

### ProsusAI/finbert
- **Source:** [ProsusAI/finbert](https://huggingface.co/ProsusAI/finbert)
- **License:** Apache 2.0
- **Purpose:** Financial sentiment analysis (positive/negative/neutral)
- **Note:** Downloaded on first use and cached locally

### all-MiniLM-L6-v2
- **Source:** [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- **License:** Apache 2.0
- **Purpose:** Sentence embeddings for event deduplication, novelty, corroboration

### facebook/bart-large-mnli
- **Source:** [facebook/bart-large-mnli](https://huggingface.co/facebook/bart-large-mnli)
- **License:** MIT
- **Purpose:** Zero-shot classification of financial events into taxonomy

## Synthetic Data

### Portfolio
- **Location:** `data/synthetic/portfolio.json`
- **Purpose:** Synthetic wholesale banking portfolio for stress testing demonstrations
- **Note:** 18 positions across 6 asset classes, $100M total

## Download Instructions

```bash
# Install dependencies
pip install datasets

# Download all datasets
python scripts/download_datasets.py
```

## Directory Structure

```
data/
├── README.md           # This file
├── raw/                # Downloaded HuggingFace datasets
│   ├── manifest.json   # Overall download manifest
│   ├── twitter_topic/
│   ├── twitter_sentiment/
│   └── financial_phrasebank/
└── synthetic/          # Synthetic demo data
    └── portfolio.json
```
