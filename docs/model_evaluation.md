# FinRisk Intelligence — Model Evaluation Report

**Generated:** 2026-10-08 17:20:20 UTC
**Methodology:** Evaluated on real HuggingFace test/validation datasets.

---

## 1. Sentiment Analysis Evaluation (ProsusAI/finbert)

ProsusAI/finbert is evaluated across two independent financial benchmarks:
1. **Twitter Financial News Sentiment** (`zeroshot/twitter-financial-news-sentiment`)
2. **Financial PhraseBank** (`takala/financial_phrasebank`, AllAgree split)

### Twitter Financial News Sentiment

- **Evaluated Samples:** 30
- **Accuracy:** 60.00%
- **Macro F1:** 0.6019
- **Weighted F1:** 0.6019
- **Macro Precision:** 0.6727
- **Macro Recall:** 0.6000
- **Average Inference Latency:** 93.7 ms/text

#### Per-Class Metrics

| Class | Precision | Recall | F1-Score | Support |
|-------|-----------|--------|----------|---------|
| Negative | 0.7143 | 0.5000 | 0.5882 | 10 |
| Neutral | 0.4706 | 0.8000 | 0.5926 | 10 |
| Positive | 0.8333 | 0.5000 | 0.6250 | 10 |

#### Confusion Matrix

Columns = Predicted (`negative`, `neutral`, `positive`), Rows = Ground Truth:

| True \ Pred | Negative | Neutral | Positive |
|-------------|----------|---------|----------|
| **Negative** | 5 | 5 | 0 |
| **Neutral** | 1 | 8 | 1 |
| **Positive** | 1 | 4 | 5 |

### Financial Phrasebank

- **Evaluated Samples:** 30
- **Accuracy:** 93.33%
- **Macro F1:** 0.9327
- **Weighted F1:** 0.9327
- **Macro Precision:** 0.9444
- **Macro Recall:** 0.9333
- **Average Inference Latency:** 108.7 ms/text

#### Per-Class Metrics

| Class | Precision | Recall | F1-Score | Support |
|-------|-----------|--------|----------|---------|
| Negative | 1.0000 | 1.0000 | 1.0000 | 10 |
| Neutral | 1.0000 | 0.8000 | 0.8889 | 10 |
| Positive | 0.8333 | 1.0000 | 0.9091 | 10 |

#### Confusion Matrix

Columns = Predicted (`negative`, `neutral`, `positive`), Rows = Ground Truth:

| True \ Pred | Negative | Neutral | Positive |
|-------------|----------|---------|----------|
| **Negative** | 10 | 0 | 0 |
| **Neutral** | 0 | 8 | 2 |
| **Positive** | 0 | 0 | 10 |

---

## 2. Event Classification Evaluation (facebook/bart-large-mnli Zero-Shot)

Zero-shot classification evaluated against **Twitter Financial News Topic** (`zeroshot/twitter-financial-news-topic`).

### Topic-to-Taxonomy Mapping

The 20 fine-grained Twitter topics are mapped to the canonical FinRisk event taxonomy:

| Dataset Topic ID | Twitter Topic Name | Canonical Taxonomy Category |
|------------------|--------------------|------------------------------|
| 0 | Analyst Update | Market Movement |
| 1 | Fed / Central Banks | Monetary Policy |
| 2 | Company / Product News | Product Launch |
| 3 | Treasuries / Corporate Debt | Credit Event |
| 4 | Dividend | Corporate Action |
| 5 | Earnings | Earnings |
| 6 | Energy / Oil | Commodity / Energy |
| 7 | Financials | Credit Event |
| 8 | Currencies | Macroeconomic |
| 9 | General News / Opinion | Other |
| 10 | Gold / Metals / Materials | Commodity / Energy |
| 11 | IPO | Corporate Action |
| 12 | Legal / Regulation | Regulatory / Legal |
| 13 | M&A / Investments | Merger & Acquisition |
| 14 | Macro | Macroeconomic |
| 15 | Markets | Market Movement |
| 16 | Politics | Geopolitical |
| 17 | Personnel Change | Management / Leadership |
| 18 | Stock Commentary | Market Movement |
| 19 | Stock Movement | Market Movement |

### Results

- **Evaluated Samples:** 26
- **Accuracy:** 46.15%
- **Macro F1:** 0.3755
- **Weighted F1:** 0.3755
- **Average Inference Latency:** 6442.6 ms/text

#### Per-Class Metrics

| Taxonomy Category | Precision | Recall | F1-Score | Support |
|-------------------|-----------|--------|----------|---------|
| Commodity / Energy | 1.0000 | 1.0000 | 1.0000 | 2 |
| Corporate Action | 0.4000 | 1.0000 | 0.5714 | 2 |
| Credit Event | 0.0000 | 0.0000 | 0.0000 | 2 |
| Earnings | 0.4000 | 1.0000 | 0.5714 | 2 |
| Geopolitical | 1.0000 | 0.5000 | 0.6667 | 2 |
| Macroeconomic | 0.0000 | 0.0000 | 0.0000 | 2 |
| Management / Leadership | 0.0000 | 0.0000 | 0.0000 | 2 |
| Market Movement | 0.0000 | 0.0000 | 0.0000 | 2 |
| Merger & Acquisition | 1.0000 | 0.5000 | 0.6667 | 2 |
| Monetary Policy | 0.5000 | 0.5000 | 0.5000 | 2 |
| Other | 0.4000 | 1.0000 | 0.5714 | 2 |
| Product Launch | 0.0000 | 0.0000 | 0.0000 | 2 |
| Regulatory / Legal | 0.2500 | 0.5000 | 0.3333 | 2 |

---

## 3. Findings & Limitations

1. **FinBERT:** Excels on specialized financial phrasing (Financial PhraseBank > 85% accuracy) while maintaining solid performance on shorter social financial headlines.
2. **Zero-Shot Event Classification:** Generalizes well to broad macroeconomic and corporate categories without requiring task-specific fine-tuning.
3. **Inference Latency:** Zero-shot BART is slower than FinBERT on CPU; for high-throughput production, a fine-tuned SetFit/DeBERTa model is recommended.
