"""
Model evaluation script for FinRisk Intelligence.

Evaluates the actual FinBERT sentiment model and zero-shot event classifier
against benchmark examples with known correct labels.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))


SENTIMENT_BENCHMARK: List[Tuple[str, str]] = [
    ("Inflation remains stubborn and could pressure profit margins significantly.", "negative"),
    ("Demand trends improve and margins expand across the sector.", "positive"),
    ("Markets remain stable after the policy signal.", "neutral"),
    ("Oil prices surge on escalating geopolitical tensions.", "negative"),
    ("Strong quarterly earnings beat analyst expectations.", "positive"),
    ("Credit rating agency downgrades several major banks.", "negative"),
    ("Technology sector rallies on AI infrastructure spending.", "positive"),
    ("Federal Reserve maintains current interest rate policy.", "neutral"),
    ("Major supply chain disruption at Asian manufacturing facilities.", "negative"),
    ("Company reports revenue growth of 15% year over year.", "positive"),
]

EVENT_BENCHMARK: List[Tuple[str, str]] = [
    ("Fed signals aggressive rate increases amid inflation pressure.", "Monetary Policy"),
    ("Apple supplier network faces critical supply chain disruption.", "Supply Chain"),
    ("Bank under investigation for credit risk irregularities.", "Regulatory / Legal"),
    ("Oil prices surge on Middle East conflict escalation.", "Geopolitical"),
    ("Major bank announces quarterly earnings above expectations.", "Earnings"),
    ("Central bank holds rates steady as inflation moderates.", "Monetary Policy"),
    ("Company completes acquisition of competitor for $5 billion.", "Merger & Acquisition"),
    ("Credit spreads widen as default risks increase in corporate bonds.", "Credit Event"),
]


def evaluate() -> Dict[str, object]:
    """Evaluate models against benchmark data."""
    print("=" * 60)
    print("FinRisk Intelligence — Model Evaluation")
    print("=" * 60)

    results: Dict[str, object] = {}

    # ── Sentiment Evaluation ────────────────────────────
    print("\n--- Sentiment Analysis (FinBERT) ---")
    try:
        from app.core.model_manager import get_model_manager
        mm = get_model_manager()
        mm.load_finbert()

        correct = 0
        total = len(SENTIMENT_BENCHMARK)
        t0 = time.time()

        for text, expected in SENTIMENT_BENCHMARK:
            result = mm.analyze_sentiment(text)
            predicted = result["label"]
            match = predicted == expected
            if match:
                correct += 1
            status = "✓" if match else "✗"
            print(f"  {status} Expected={expected:8s} Got={predicted:8s} Score={result['score']:+.3f} | {text[:60]}...")

        sentiment_acc = round(correct / total, 4)
        sentiment_time = round((time.time() - t0) * 1000 / total, 1)
        results["sentiment_accuracy"] = sentiment_acc
        results["sentiment_model"] = mm._finbert_status
        results["sentiment_avg_ms"] = sentiment_time
        print(f"\n  Accuracy: {correct}/{total} = {sentiment_acc:.2%}")
        print(f"  Avg inference: {sentiment_time}ms per text")

    except Exception as exc:
        print(f"  ERROR: {exc}")
        results["sentiment_accuracy"] = 0.0
        results["sentiment_error"] = str(exc)

    # ── Event Classification Evaluation ─────────────────
    print("\n--- Event Classification (Zero-Shot) ---")
    try:
        mm = get_model_manager()
        mm.load_classifier()

        correct = 0
        total = len(EVENT_BENCHMARK)
        t0 = time.time()

        for text, expected in EVENT_BENCHMARK:
            result = mm.classify_event(text)
            predicted = result["class"]
            match = predicted == expected
            if match:
                correct += 1
            status = "✓" if match else "✗"
            print(f"  {status} Expected={expected:25s} Got={predicted:25s} Conf={result['confidence']:.3f} | {text[:50]}...")

        event_acc = round(correct / total, 4)
        event_time = round((time.time() - t0) * 1000 / total, 1)
        results["event_accuracy"] = event_acc
        results["event_model"] = mm._classifier_status
        results["event_avg_ms"] = event_time
        print(f"\n  Accuracy: {correct}/{total} = {event_acc:.2%}")
        print(f"  Avg inference: {event_time}ms per text")

    except Exception as exc:
        print(f"  ERROR: {exc}")
        results["event_accuracy"] = 0.0
        results["event_error"] = str(exc)

    # ── Embedding Evaluation ────────────────────────────
    print("\n--- Embedding Model ---")
    try:
        mm = get_model_manager()
        mm.load_embeddings()

        t0 = time.time()
        embeddings = mm.encode(["Test financial sentence about market volatility."])
        embed_time = round((time.time() - t0) * 1000, 1)
        results["embedding_model"] = mm._embedding_status
        results["embedding_dim"] = int(embeddings.shape[1])
        results["embedding_ms"] = embed_time
        print(f"  Status: {mm._embedding_status}")
        print(f"  Dimension: {embeddings.shape[1]}")
        print(f"  Inference: {embed_time}ms")

    except Exception as exc:
        print(f"  ERROR: {exc}")
        results["embedding_error"] = str(exc)

    # ── Summary ─────────────────────────────────────────
    results["note"] = (
        "Evaluation against small hand-labelled benchmark. "
        "Larger-scale evaluation on downloaded datasets can be done separately."
    )

    print("\n" + "=" * 60)
    print("Summary:")
    print(json.dumps(results, indent=2))
    print("=" * 60)

    # Save results
    out_path = Path(__file__).resolve().parents[1] / "docs" / "evaluation_results.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Results saved to {out_path}")

    return results


if __name__ == "__main__":
    evaluate()
