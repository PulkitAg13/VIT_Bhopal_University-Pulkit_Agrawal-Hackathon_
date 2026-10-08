"""Targeted tests for required pipeline and API behaviors.

Tests:
1. NER unavailable causes controlled model-unavailable behavior.
2. Duplicate ingestion returns already_processed.
3. Non-eligible high-impact event does not trigger stress.
4. Eligible high-impact event persists an automatic StressSimulation.
5. Events sentiment filter works.
6. Events source filter works.
"""
from __future__ import annotations

import uuid
import pytest

from app.core.model_manager import get_model_manager, ModelUnavailableError
from app.models import StressSimulation
from app.services.risk.risk_fusion import RiskFusionService


def test_ner_unavailable_causes_model_unavailable(client):
    """Test 1: NER unavailable causes controlled model-unavailable behavior (HTTP 503)."""
    mm = get_model_manager()
    original_ner = mm._ner_pipeline
    original_status = mm._ner_status
    try:
        mm._ner_pipeline = None
        mm._ner_status = "error: mock NER failure"

        # Direct manager check
        with pytest.raises(ModelUnavailableError) as exc_info:
            mm.check_mandatory_models()
        assert "dslim/bert-base-NER" in str(exc_info.value)

        # /analyze endpoint returns controlled 503
        resp = client.post("/api/v1/analyze", json={
            "text": "Apple Inc announces record quarterly revenue and dividends.",
            "source_name": "Reuters",
        })
        assert resp.status_code == 503
        data = resp.json()
        assert data.get("error_code") == "MODEL_UNAVAILABLE"
        assert data.get("model") == "dslim/bert-base-NER"
    finally:
        mm._ner_pipeline = original_ner
        mm._ner_status = original_status


def test_duplicate_ingestion_returns_already_processed(client):
    """Test 2: Duplicate ingestion returns already_processed."""
    unique_text = f"Federal Reserve unexpected interest rate cut announced today {uuid.uuid4().hex}."

    resp1 = client.post("/api/v1/analyze", json={
        "text": unique_text,
        "source_name": "Bloomberg",
        "source_type": "rss",
    })
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert not data1.get("already_processed")

    resp2 = client.post("/api/v1/analyze", json={
        "text": unique_text,
        "source_name": "Bloomberg",
        "source_type": "rss",
    })
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2.get("already_processed") is True
    assert data2["signal_id"] == data1["signal_id"]


def test_non_eligible_high_impact_event_does_not_trigger_stress(db_session, monkeypatch):
    """Test 3: Non-eligible high-impact event does not trigger stress."""
    rf = RiskFusionService()
    monkeypatch.setattr(
        "app.services.risk.risk_fusion.classify_event",
        lambda text: {"class": "Product Launch", "confidence": 0.95, "model": "test"},
    )
    monkeypatch.setattr(
        "app.services.risk.risk_fusion.compute_impact_score",
        lambda payload: {
            "score": 8.5,
            "risk_level": "HIGH",
            "components": {},
            "unavailable_components": [],
            "methodology": "test",
            "explanation": "High impact test",
        },
    )

    result = rf.analyze(
        text=f"Company unveils innovative quantum computing chip architecture {uuid.uuid4().hex}.",
        source_name="TechNews",
        db=db_session,
    )
    assert result["impact"]["score"] >= 7.0
    assert result["stress_test"]["triggered"] is False
    assert result["stress_test"]["result"] is None

    sim = db_session.query(StressSimulation).filter(
        StressSimulation.trigger_signal_id == result["signal_id"]
    ).first()
    assert sim is None


def test_eligible_high_impact_event_persists_automatic_stress_simulation(db_session, monkeypatch):
    """Test 4: Eligible high-impact event persists an automatic StressSimulation."""
    rf = RiskFusionService()
    monkeypatch.setattr(
        "app.services.risk.risk_fusion.classify_event",
        lambda text: {"class": "Geopolitical", "confidence": 0.95, "model": "test"},
    )
    monkeypatch.setattr(
        "app.services.risk.risk_fusion.compute_impact_score",
        lambda payload: {
            "score": 8.5,
            "risk_level": "HIGH",
            "components": {},
            "unavailable_components": [],
            "methodology": "test",
            "explanation": "High impact geopolitical shock",
        },
    )

    result = rf.analyze(
        text=f"Severe geopolitical military conflict escalates across key maritime trade corridors {uuid.uuid4().hex}.",
        source_name="GlobalNews",
        db=db_session,
    )
    assert result["impact"]["score"] >= 7.0
    assert result["stress_test"]["triggered"] is True
    assert result["stress_test"]["scenario"] == "GEOPOLITICAL_SHOCK"

    sim = db_session.query(StressSimulation).filter(
        StressSimulation.trigger_signal_id == result["signal_id"]
    ).first()
    assert sim is not None
    assert sim.scenario_name == "GEOPOLITICAL_SHOCK"
    assert sim.is_auto_triggered is True
    assert sim.loss_percentage >= 0


def test_events_sentiment_filter_works(client):
    """Test 5: Events sentiment filter works."""
    client.post("/api/v1/analyze", json={
        "text": f"Quarterly revenue and earnings surge significantly exceeding expectations {uuid.uuid4().hex}.",
        "source_name": "Reuters",
    })
    client.post("/api/v1/analyze", json={
        "text": f"Severe debt default and bankruptcy liquidation announced {uuid.uuid4().hex}.",
        "source_name": "Bloomberg",
    })

    resp_pos = client.get("/api/v1/events?sentiment=positive")
    assert resp_pos.status_code == 200
    data_pos = resp_pos.json()
    assert "items" in data_pos
    for item in data_pos["items"]:
        assert item["sentiment"]["label"] == "positive"

    resp_neg = client.get("/api/v1/events?sentiment=negative")
    assert resp_neg.status_code == 200
    data_neg = resp_neg.json()
    assert "items" in data_neg
    for item in data_neg["items"]:
        assert item["sentiment"]["label"] == "negative"


def test_events_source_filter_works(client):
    """Test 6: Events source filter works."""
    unique_src1 = f"AlphaNewswire_{uuid.uuid4().hex[:6]}"
    unique_src2 = f"BetaReport_{uuid.uuid4().hex[:6]}"

    client.post("/api/v1/analyze", json={
        "text": f"Market rally continues with positive equity momentum {uuid.uuid4().hex}.",
        "source_name": unique_src1,
    })
    client.post("/api/v1/analyze", json={
        "text": f"Central banks evaluate monetary adjustments {uuid.uuid4().hex}.",
        "source_name": unique_src2,
    })

    resp = client.get(f"/api/v1/events?source={unique_src1}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    for item in data["items"]:
        src_match = (
            unique_src1.lower() in (item.get("source_name") or "").lower()
            or unique_src1.lower() in (item.get("source", {}).get("type") or "").lower()
        )
        assert src_match
