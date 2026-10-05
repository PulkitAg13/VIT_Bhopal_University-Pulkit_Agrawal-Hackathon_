from app.services.stress.stress_engine import StressEngine


def test_stress_engine_scenarios():
    engine = StressEngine()
    scenarios = engine.get_scenarios()
    names = [s["name"] for s in scenarios]
    assert "GEOPOLITICAL_SHOCK" in names
    assert "MACRO_RATE_SHOCK" in names
    assert "CREDIT_CRISIS" in names
    assert "LIQUIDITY_SHOCK" in names
    assert "COMMODITY_SHOCK" in names


def test_stress_engine_duration_sensitive_bonds(db_session):
    engine = StressEngine()
    portfolio = {
        "portfolio_id": "test-portfolio",
        "total_value": 20_000_000,
        "positions": [
            {
                "asset_id": "GB-LONG",
                "asset_class": "Government Bonds",
                "issuer": "US Treasury",
                "notional": 10_000_000,
                "duration": 10.0,
            },
            {
                "asset_id": "GB-SHORT",
                "asset_class": "Government Bonds",
                "issuer": "US Treasury",
                "notional": 10_000_000,
                "duration": 2.0,
            },
        ],
    }

    result = engine.stress_test(portfolio, "MACRO_RATE_SHOCK", db=db_session)
    impacts = {item["asset_id"]: item for item in result["asset_level_impacts"]}

    # Longer duration bond must suffer greater price decline under rate shock
    long_loss_pct = abs(impacts["GB-LONG"]["impact_pct"])
    short_loss_pct = abs(impacts["GB-SHORT"]["impact_pct"])
    assert long_loss_pct > short_loss_pct
    assert result["portfolio_after"] < result["portfolio_before"]
