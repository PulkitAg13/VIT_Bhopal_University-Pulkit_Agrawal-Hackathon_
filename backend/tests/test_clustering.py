"""Test event clustering and lifecycle status computation."""
import numpy as np
from datetime import datetime, timezone, timedelta
from app.models import EventCluster
from app.services.risk.risk_fusion import RiskFusionService


def test_cluster_creation_and_centroid_update(db_session):
    rf = RiskFusionService()
    emb1 = np.ones(384, dtype=np.float32)
    emb1 = emb1 / np.linalg.norm(emb1)

    # 1. Create first cluster
    c1 = rf._find_or_create_cluster(
        emb1, "Monetary Policy", ["Federal Reserve"],
        "Federal Reserve raises rates by 50bps.",
        db_session,
    )
    assert c1 is not None
    assert c1.event_count == 1
    assert c1.status == "NEW"
    db_session.flush()

    # 2. Add highly similar event
    emb2 = emb1.copy() + np.random.normal(0, 0.001, 384).astype(np.float32)
    emb2 = emb2 / np.linalg.norm(emb2)

    c2 = rf._find_or_create_cluster(
        emb2, "Monetary Policy", ["Federal Reserve"],
        "Fed continues rate hikes amid inflation concerns.",
        db_session,
    )
    assert c2.id == c1.id
    assert c2.event_count == 2


def test_cluster_lifecycle_computation(db_session):
    rf = RiskFusionService()
    now = datetime.now(timezone.utc)

    # NEW cluster
    c_new = EventCluster(event_count=1, first_seen=now, last_updated=now)
    assert rf._compute_cluster_status(c_new) == "NEW"

    # ESCALATING cluster (high frequency)
    c_esc = EventCluster(event_count=10, first_seen=now - timedelta(hours=2), last_updated=now)
    assert rf._compute_cluster_status(c_esc) == "ESCALATING"

    # RESOLVED cluster (inactive > 24 hours with multiple events)
    c_res = EventCluster(event_count=5, first_seen=now - timedelta(days=2), last_updated=now - timedelta(hours=25))
    assert rf._compute_cluster_status(c_res) == "RESOLVED"
