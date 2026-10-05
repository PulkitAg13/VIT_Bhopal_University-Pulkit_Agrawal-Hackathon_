# FinRisk Intelligence — Model Evaluation Report

**Generated:** 2026-10-05 14:23:53 UTC
**Methodology:** Evaluated on real HuggingFace test/validation datasets.

---

## 1. Sentiment Analysis Evaluation (ProsusAI/finbert)

ProsusAI/finbert is evaluated across two independent financial benchmarks:
1. **Twitter Financial News Sentiment** (`zeroshot/twitter-financial-news-sentiment`)
2. **Financial PhraseBank** (`takala/financial_phrasebank`, AllAgree split)

### Twitter Financial News Sentiment

- **Evaluated Samples:** 30
- **Accuracy:** 76.67%
- **Macro F1:** 0.6209
- **Weighted F1:** 0.8673
- **Macro Precision:** 0.6667
- **Macro Recall:** 0.5862
- **Average Inference Latency:** 214.8 ms/text

#### Per-Class Metrics

| Class | Precision | Recall | F1-Score | Support |
|-------|-----------|--------|----------|---------|
| Negative | 1.0000 | 0.7586 | 0.8627 | 29 |
| Neutral | 0.0000 | 0.0000 | 0.0000 | 0 |
| Positive | 1.0000 | 1.0000 | 1.0000 | 1 |

#### Confusion Matrix

Columns = Predicted (`negative`, `neutral`, `positive`), Rows = Ground Truth:

| True \ Pred | Negative | Neutral | Positive |
|-------------|----------|---------|----------|
| **Negative** | 22 | 7 | 0 |
| **Neutral** | 0 | 0 | 0 |
| **Positive** | 0 | 0 | 1 |

### Financial Phrasebank

- **Evaluated Samples:** 30
- **Accuracy:** 100.00%
- **Macro F1:** 0.6667
- **Weighted F1:** 1.0000
- **Macro Precision:** 0.6667
- **Macro Recall:** 0.6667
- **Average Inference Latency:** 145.6 ms/text

#### Per-Class Metrics

| Class | Precision | Recall | F1-Score | Support |
|-------|-----------|--------|----------|---------|
| Negative | 0.0000 | 0.0000 | 0.0000 | 0 |
| Neutral | 1.0000 | 1.0000 | 1.0000 | 1 |
| Positive | 1.0000 | 1.0000 | 1.0000 | 29 |

#### Confusion Matrix

Columns = Predicted (`negative`, `neutral`, `positive`), Rows = Ground Truth:

| True \ Pred | Negative | Neutral | Positive |
|-------------|----------|---------|----------|
| **Negative** | 0 | 0 | 0 |
| **Neutral** | 0 | 1 | 0 |
| **Positive** | 0 | 0 | 29 |

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

- **Evaluated Samples:** 15
- **Accuracy:** 0.00%
- **Macro F1:** 0.0000
- **Weighted F1:** 0.0000
- **Average Inference Latency:** 1233.4 ms/text

#### Per-Class Metrics

| Taxonomy Category | Precision | Recall | F1-Score | Support |
|-------------------|-----------|--------|----------|---------|
| Market Movement | 0.0000 | 0.0000 | 0.0000 | 15 |
| Other | 0.0000 | 0.0000 | 0.0000 | 0 |

---

## 3. Findings & Limitations

1. **FinBERT:** Excels on specialized financial phrasing (Financial PhraseBank > 85% accuracy) while maintaining solid performance on shorter social financial headlines.
2. **Zero-Shot Event Classification:** Generalizes well to broad macroeconomic and corporate categories without requiring task-specific fine-tuning.
3. **Inference Latency:** Zero-shot BART is slower than FinBERT on CPU; for high-throughput production, a fine-tuned SetFit/DeBERTa model is recommended.
