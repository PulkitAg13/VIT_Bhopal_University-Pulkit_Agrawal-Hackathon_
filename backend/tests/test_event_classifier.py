import pytest
from app.services.nlp.event_classifier import classify_event


def test_event_classifier_structure():
    result = classify_event("Federal Reserve raises interest rates by 50 basis points to curb persistent inflation.")
    assert "class" in result
    assert "confidence" in result
    assert "all_scores" in result
    assert 0.0 <= result["confidence"] <= 1.0
    assert isinstance(result["all_scores"], dict)


def test_event_classifier_monetary_policy():
    result = classify_event("Central bank announces benchmark rate hike of 75 basis points.")
    assert result["class"] in ["Monetary Policy", "Macroeconomic"]
    assert result["confidence"] > 0.3


def test_event_classifier_earnings():
    result = classify_event("Technology corporation posts Q3 net income and earnings per share well above guidance.")
    assert result["class"] in ["Earnings", "Corporate Action", "Market Movement"]
