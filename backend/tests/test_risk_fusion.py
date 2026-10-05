from app.services.risk.risk_fusion import RiskFusionService


def test_risk_fusion_complete_pipeline(db_session):
    rf = RiskFusionService()
    text = (
        "Severe escalation in Middle East military conflict threatens oil transit routes, "
        "sending crude prices sharply higher and raising inflation fears globally."
    )
    result = rf.analyze(
        text=text,
        source_name="Reuters",
        source_type="rss",
        db=db_session,
    )

    assert "signal_id" in result
    assert "sentiment" in result
    assert "event" in result
    assert "impact" in result
    assert 1.0 <= result["impact"]["score"] <= 10.0
    assert result["impact"]["risk_level"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]
    assert "novelty_score" in result
    assert "corroboration" in result
    assert "stress_test" in result
    assert "explanation" in result


def test_risk_fusion_high_impact_stress_trigger(db_session):
    rf = RiskFusionService()
    # High impact crisis statement
    crisis_text = (
        "Massive global liquidity freeze and credit defaults cascade across financial institutions "
        "prompting emergency regulatory interventions and severe equity market sell-offs."
    )
    result = rf.analyze(
        text=crisis_text,
        source_name="Financial Times",
        source_type="rss",
        db=db_session,
    )

    # If impact >= 7 and eligible category, stress_test is triggered
    if result["impact"]["score"] >= 7.0 and result["event"]["class"] in [
        "Credit Event", "Geopolitical", "Macroeconomic", "Liquidity", "Commodity / Energy", "Monetary Policy"
    ]:
        assert result["stress_test"]["triggered"] is True
        assert result["stress_test"]["result"] is not None
        assert "loss_percentage" in result["stress_test"]["result"]
