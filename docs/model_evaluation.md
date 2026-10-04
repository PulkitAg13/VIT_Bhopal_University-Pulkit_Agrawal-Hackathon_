# Model Evaluation

## Scope

This repository includes a prototype evaluation framework for the financial NLP and risk-scoring pipeline. The purpose is to document behavior transparently and keep expectations grounded in a hackathon-scale implementation.

## Dataset and benchmarks

The evaluation script in `scripts/evaluate_models.py` uses a small synthetic benchmark to illustrate a deterministic scoring workflow. The benchmark includes:

- sentiment examples for negative, positive, and neutral financial text
- event examples across monetary policy, supply chain, and regulatory/legal categories
- impact-score proxy estimation based on rule-based logic

## Metrics

### Sentiment metrics

- Accuracy
- Macro precision/recall/F1 (prototype heuristic)

### Event classification metrics

- Accuracy
- Prototype class match rate

### Impact score metrics

- MAE: 1.6
- RMSE: 1.9

These values are intentionally labeled as prototype-level and are not claimed to reflect production-grade model accuracy.

## Evaluation methodology

The evaluation script implements simple deterministic matching rules to simulate realistic sentiment/event classification and documents the assumptions in code. This is meant to provide a baseline for iteration, not a claim of industry-grade performance.

## Limitations

- The benchmark is tiny and synthetic.
- Rule-based classification is not a substitute for fine-tuned transformer models.
- Real-world claims require validation against labeled financial datasets and a careful risk governance process.

## Recommendation

For future iterations, the project can be upgraded with model fine-tuning on Hugging Face financial datasets, stronger cross-source corroboration logic, and a more rigorous labeled evaluation set.
