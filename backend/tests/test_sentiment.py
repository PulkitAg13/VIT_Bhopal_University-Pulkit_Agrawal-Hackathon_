import pytest
from app.services.nlp.sentiment import sentiment_analysis


def test_sentiment_structure():
    result = sentiment_analysis("Company reports record high quarterly profits and surging operating margins.")
    assert "label" in result
    assert "score" in result
    assert "confidence" in result
    assert "probabilities" in result
    assert result["label"] in ["positive", "neutral", "negative"]
    assert -1.0 <= result["score"] <= 1.0
    assert 0.0 <= result["confidence"] <= 1.0


def test_sentiment_positive_signal():
    result = sentiment_analysis("Strong revenue growth and upgraded earnings outlook across all business units.")
    assert result["label"] == "positive"
    assert result["score"] > 0.0


def test_sentiment_negative_signal():
    result = sentiment_analysis("Company warns of catastrophic losses, impending bankruptcy, and massive asset write-downs.")
    assert result["label"] == "negative"
    assert result["score"] < 0.0
