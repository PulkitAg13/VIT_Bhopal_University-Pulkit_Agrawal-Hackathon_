"""Tests for yfinance market context enrichment, caching, and rate-limit cooldown."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import pandas as pd

from app.services.risk.risk_fusion import MarketContextService, RiskFusionService


@pytest.fixture(autouse=True)
def reset_market_context():
    """Reset MarketContextService state before and after each test."""
    MarketContextService.clear_cache()
    original_bypass = MarketContextService._bypass_in_tests
    original_cooldown_ttl = MarketContextService._cooldown_ttl
    MarketContextService._bypass_in_tests = False
    yield
    MarketContextService.clear_cache()
    MarketContextService._bypass_in_tests = original_bypass
    MarketContextService._cooldown_ttl = original_cooldown_ttl


def _create_mock_price_df(length=10):
    dates = pd.date_range("2026-01-01", periods=length)
    prices = [100.0 + i * 1.5 for i in range(length)]
    return pd.DataFrame({"Close": prices}, index=dates)


def test_yfinance_success_enrichment():
    """Test successful yfinance market data fetch and volatility computation."""
    mock_df = _create_mock_price_df()
    mock_stock = MagicMock()
    mock_stock.history.return_value = mock_df

    with patch("yfinance.Ticker", return_value=mock_stock) as mock_ticker:
        result = MarketContextService.get_market_context([{"ticker": "SPY", "type": "company"}])

        assert result["market_context_available"] is True
        assert result["market_volatility"] >= 0.0
        assert result["avg_realized_volatility"] > 0.0
        assert result["data_source"] == "yfinance"
        assert result["tickers_checked"] == ["SPY"]
        assert mock_ticker.call_count == 1
        assert "SPY" in MarketContextService._cache


def test_yfinance_success_caching_avoids_repeated_requests():
    """Test that multiple events in a batch reuse cached SPY data without repeated calls."""
    mock_df = _create_mock_price_df()
    mock_stock = MagicMock()
    mock_stock.history.return_value = mock_df

    with patch("yfinance.Ticker", return_value=mock_stock) as mock_ticker:
        # First call fetches and caches
        res1 = MarketContextService.get_market_context([])
        assert res1["market_context_available"] is True
        assert mock_ticker.call_count == 1

        # Subsequent 4 calls for same batch (defaults to SPY) must use cache
        for _ in range(4):
            res = MarketContextService.get_market_context([])
            assert res["market_context_available"] is True
            assert res["market_volatility"] == res1["market_volatility"]

        # Ticker should have been called strictly ONCE
        assert mock_ticker.call_count == 1


def test_yfinance_rate_limit_failure_fails_fast_with_fallback():
    """Test rate-limit failure activates cooldown and returns standard fallback."""
    mock_stock = MagicMock()
    mock_stock.history.side_effect = Exception("Too Many Requests. Rate limited. Try after a while.")

    with patch("yfinance.Ticker", return_value=mock_stock) as mock_ticker:
        result = MarketContextService.get_market_context([])

        assert result["market_context_available"] is False
        assert result["market_volatility"] == 0.0
        assert "Market data unavailable" in result["note"]
        assert mock_ticker.call_count == 1
        assert MarketContextService._provider_cooldown_until is not None
        assert "SPY" in MarketContextService._failure_cooldowns


def test_repeated_calls_after_rate_limit_do_not_hit_yfinance():
    """Test that repeated requests after rate limit do not repeatedly hit external API."""
    mock_stock = MagicMock()
    mock_stock.history.side_effect = Exception("Too Many Requests. Rate limited. Try after a while.")

    with patch("yfinance.Ticker", return_value=mock_stock) as mock_ticker:
        # 1st call encounters rate limit and enters cooldown
        res1 = MarketContextService.get_market_context([])
        assert res1["market_context_available"] is False
        assert mock_ticker.call_count == 1

        # 4 subsequent calls during replay/ingestion must skip yfinance entirely
        for _ in range(4):
            res = MarketContextService.get_market_context([])
            assert res["market_context_available"] is False
            assert res["market_volatility"] == 0.0

        # Ticker was called strictly ONCE, not 5 times
        assert mock_ticker.call_count == 1


def test_rate_limit_cooldown_expiration():
    """Test that after cooldown expires, yfinance is queried again."""
    import time
    MarketContextService._cooldown_ttl = timedelta(milliseconds=50)

    mock_stock = MagicMock()
    mock_stock.history.side_effect = Exception("429 Too Many Requests")

    with patch("yfinance.Ticker", return_value=mock_stock) as mock_ticker:
        res1 = MarketContextService.get_market_context([])
        assert res1["market_context_available"] is False
        assert mock_ticker.call_count == 1

        # Immediate call is blocked by cooldown
        res2 = MarketContextService.get_market_context([])
        assert mock_ticker.call_count == 1

        # Wait for cooldown to expire
        time.sleep(0.06)

        # After expiry, attempts query again
        res3 = MarketContextService.get_market_context([])
        assert mock_ticker.call_count == 2


def test_risk_fusion_pipeline_with_rate_limited_yfinance(db_session):
    """Test that the NLP and risk analysis pipeline runs cleanly when yfinance is rate-limited."""
    mock_stock = MagicMock()
    mock_stock.history.side_effect = Exception("Too Many Requests. Rate limited. Try after a while.")

    with patch("yfinance.Ticker", return_value=mock_stock) as mock_ticker:
        rf = RiskFusionService()
        result = rf.analyze(
            text="Central bank unexpectedly increases interest rates by 50 bps amid persistent inflation.",
            source_name="Financial Times",
            source_type="rss",
            db=db_session,
        )

        assert "signal_id" in result
        assert "sentiment" in result
        assert "event" in result
        assert "impact" in result
        assert result["market_context"]["market_context_available"] is False
        assert result["market_context_available"] is False
        assert mock_ticker.call_count == 1

        # Second analysis event in same operation hits cooldown without querying yfinance
        result2 = rf.analyze(
            text="Tech equities retreat following central bank hawkish statements.",
            source_name="Bloomberg",
            source_type="rss",
            db=db_session,
        )
        assert result2["market_context"]["market_context_available"] is False
        assert mock_ticker.call_count == 1  # Still 1!


def test_ingestion_api_completes_when_yfinance_rate_limited(client):
    """Test that /api/v1/ingest returns 200 OK when external market provider is rate-limited."""
    from unittest.mock import patch

    # Mock risk_service.analyze to avoid heavy torch thread loads inside TestClient
    with patch("app.api.routes.ingestion.risk_service") as mock_rs:
        mock_rs.analyze.return_value = {
            "signal_id": "test-signal-123",
            "market_context_available": False,
            "impact": {"score": 5.0, "risk_level": "MODERATE"},
        }
        response = client.post("/api/v1/ingest", json={
            "source": "demo",
            "max_items": 3,
        })

        assert response.status_code == 200
        data = response.json()
        assert data["ingested"] == 3
        assert len(data["signals"]) == 3
