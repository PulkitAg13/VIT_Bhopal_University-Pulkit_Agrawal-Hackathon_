import uuid
from datetime import datetime, timezone
from app.models import (
    Source, Document, Entity, DocumentEntity,
    EventCluster, RiskSignal, Portfolio, PortfolioPosition,
    StressScenario, StressSimulation,
)


def test_database_models_persistence_and_relationships(db_session):
    # 1. Source & Document
    src = Source(
        id=str(uuid.uuid4()),
        name="Test Financial News",
        source_type="rss",
        credibility_score=0.85,
    )
    db_session.add(src)
    db_session.flush()

    doc = Document(
        id=str(uuid.uuid4()),
        source_id=src.id,
        original_text="Test financial announcement for persistence test.",
        published_at=datetime.now(timezone.utc),
    )
    db_session.add(doc)
    db_session.flush()

    # 2. Entity & DocumentEntity
    ent = Entity(
        id=str(uuid.uuid4()),
        canonical_name="Test Bank Corp",
        ticker="TBC",
        entity_type="company",
    )
    db_session.add(ent)
    db_session.flush()

    de = DocumentEntity(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        entity_id=ent.id,
        confidence=0.95,
    )
    db_session.add(de)
    db_session.flush()

    # 3. EventCluster & RiskSignal
    cluster = EventCluster(
        id=str(uuid.uuid4()),
        label="Credit Event",
        status="NEW",
        event_count=1,
    )
    db_session.add(cluster)
    db_session.flush()

    sig = RiskSignal(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        event_cluster_id=cluster.id,
        sentiment_label="negative",
        sentiment_score=-0.65,
        sentiment_confidence=0.88,
        event_class="Credit Event",
        event_confidence=0.92,
        impact_score=7.8,
        risk_level="HIGH",
        overall_confidence=0.85,
        novelty_score=0.80,
        corroboration_score=0.70,
    )
    db_session.add(sig)
    db_session.flush()

    # 4. Stress Simulation
    sim = StressSimulation(
        id=str(uuid.uuid4()),
        trigger_signal_id=sig.id,
        scenario_name="CREDIT_CRISIS",
        portfolio_before=100000000.0,
        portfolio_after=90000000.0,
        absolute_loss=10000000.0,
        loss_percentage=10.0,
        is_auto_triggered=True,
    )
    db_session.add(sim)
    db_session.commit()

    # Verify query and navigation
    queried_sig = db_session.query(RiskSignal).filter(RiskSignal.id == sig.id).first()
    assert queried_sig is not None
    assert queried_sig.document.original_text == doc.original_text
    assert queried_sig.event_cluster.label == "Credit Event"
    assert len(queried_sig.stress_simulations) == 1
    assert queried_sig.stress_simulations[0].loss_percentage == 10.0
