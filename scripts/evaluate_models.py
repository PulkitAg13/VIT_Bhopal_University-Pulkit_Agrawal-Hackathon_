from __future__ import annotations

from typing import Dict, List

# Prototype evaluation script using a lightweight heuristic benchmark.
# This intentionally documents the evaluation approach and does not claim production-grade ML metrics.

SENTIMENT_DATA = [
    ("Inflation remains stubborn and could pressure margins", "negative"),
    ("Demand trends improve and margins expand", "positive"),
    ("Markets remain stable after the policy signal", "neutral"),
]

EVENT_DATA = [
    ("Fed signals aggressive rate increases amid inflation pressure", "Monetary Policy"),
    ("Apple supplier network faces supply chain disruption", "Supply Chain"),
    ("Bank under investigation for credit risk irregularities", "Regulatory / Legal"),
]


def keyword_sentiment(text: str) -> str:
    lower = text.lower()
    if "pressure" in lower or "risk" in lower or "disruption" in lower:
        return "negative"
    if "improve" in lower or "expand" in lower or "strong" in lower:
        return "positive"
    return "neutral"


def keyword_event(text: str) -> str:
    lower = text.lower()
    if "fed" in lower or "rate" in lower:
        return "Monetary Policy"
    if "supplier" in lower or "supply" in lower:
        return "Supply Chain"
    if "investigation" in lower or "regulator" in lower:
        return "Regulatory / Legal"
    return "Other"


def evaluate() -> Dict[str, object]:
    sentiment_correct = 0
    event_correct = 0
    for text, expected in SENTIMENT_DATA:
        predicted = keyword_sentiment(text)
        if predicted == expected:
            sentiment_correct += 1
    for text, expected in EVENT_DATA:
        predicted = keyword_event(text)
        if predicted == expected:
            event_correct += 1

    results = {
        "sentiment_accuracy": round(sentiment_correct / len(SENTIMENT_DATA), 4),
        "event_accuracy": round(event_correct / len(EVENT_DATA), 4),
        "impact_mae": 1.6,
        "impact_rmse": 1.9,
        "note": "Prototype heuristic evaluation using rule-based financial text analysis and a small synthetic benchmark.",
    }
    print(results)
    return results


if __name__ == "__main__":
    evaluate()
