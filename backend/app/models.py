from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


class Source(Base):
    __tablename__ = "sources"

    id = Column(String(64), primary_key=True, default=new_uuid)
    name = Column(String(256), nullable=False)
    source_type = Column(String(64), nullable=False)  # rss, dataset, demo, api
    credibility_score = Column(Float, default=0.7)
    credibility_label = Column(String(128), default="Prototype source credibility assumption")
    url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    documents = relationship("Document", back_populates="source")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(64), primary_key=True, default=new_uuid)
    source_id = Column(String(64), ForeignKey("sources.id"), nullable=True)
    original_text = Column(Text, nullable=False)
    source_url = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    retrieved_at = Column(DateTime(timezone=True), default=utcnow)
    embedding_vector = Column(JSON, nullable=True)  # stored as list of floats
    created_at = Column(DateTime(timezone=True), default=utcnow)

    source = relationship("Source", back_populates="documents")
    risk_signals = relationship("RiskSignal", back_populates="document")
    document_entities = relationship("DocumentEntity", back_populates="document")


class Entity(Base):
    __tablename__ = "entities"

    id = Column(String(64), primary_key=True, default=new_uuid)
    canonical_name = Column(String(256), nullable=False, unique=True)
    ticker = Column(String(16), nullable=True)
    entity_type = Column(String(64), nullable=False)  # company, institution, commodity, currency, region, macro
    created_at = Column(DateTime(timezone=True), default=utcnow)

    document_entities = relationship("DocumentEntity", back_populates="entity")

    __table_args__ = (
        Index("ix_entities_ticker", "ticker"),
        Index("ix_entities_canonical_name", "canonical_name"),
    )


class DocumentEntity(Base):
    __tablename__ = "document_entities"

    id = Column(String(64), primary_key=True, default=new_uuid)
    document_id = Column(String(64), ForeignKey("documents.id"), nullable=False)
    entity_id = Column(String(64), ForeignKey("entities.id"), nullable=False)
    confidence = Column(Float, default=0.5)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    document = relationship("Document", back_populates="document_entities")
    entity = relationship("Entity", back_populates="document_entities")


class EventCluster(Base):
    __tablename__ = "event_clusters"

    id = Column(String(64), primary_key=True, default=new_uuid)
    label = Column(String(256), nullable=True)
    representative_text = Column(Text, nullable=True)
    status = Column(String(32), default="NEW")  # NEW, DEVELOPING, ESCALATING, STABLE, RESOLVED
    event_count = Column(Integer, default=1)
    first_seen = Column(DateTime(timezone=True), default=utcnow)
    last_updated = Column(DateTime(timezone=True), default=utcnow)
    centroid_embedding = Column(JSON, nullable=True)

    risk_signals = relationship("RiskSignal", back_populates="event_cluster")

    __table_args__ = (
        Index("ix_event_clusters_status", "status"),
    )


class RiskSignal(Base):
    __tablename__ = "risk_signals"

    id = Column(String(64), primary_key=True, default=new_uuid)
    document_id = Column(String(64), ForeignKey("documents.id"), nullable=False)
    event_cluster_id = Column(String(64), ForeignKey("event_clusters.id"), nullable=True)

    # Sentiment
    sentiment_label = Column(String(16), nullable=False)
    sentiment_score = Column(Float, nullable=False)
    sentiment_confidence = Column(Float, nullable=False)
    sentiment_probabilities = Column(JSON, nullable=True)

    # Event classification
    event_class = Column(String(64), nullable=False)
    event_confidence = Column(Float, nullable=False)

    # Risk scores
    impact_score = Column(Float, nullable=False)
    impact_components = Column(JSON, nullable=True)
    risk_level = Column(String(16), nullable=False)  # LOW, MODERATE, HIGH, CRITICAL
    overall_confidence = Column(Float, nullable=False)
    novelty_score = Column(Float, nullable=False)
    corroboration_score = Column(Float, nullable=False)
    risk_trajectory = Column(String(32), default="STABLE")

    # Source
    source_name = Column(String(256), nullable=True)
    source_type = Column(String(64), nullable=True)
    source_credibility = Column(Float, default=0.7)

    # Meta
    explanation = Column(JSON, nullable=True)
    processing_time_ms = Column(Integer, default=0)
    market_context_available = Column(Boolean, default=False)
    status = Column(String(32), default="NEW")

    created_at = Column(DateTime(timezone=True), default=utcnow)

    document = relationship("Document", back_populates="risk_signals")
    event_cluster = relationship("EventCluster", back_populates="risk_signals")
    stress_simulations = relationship("StressSimulation", back_populates="trigger_signal")

    __table_args__ = (
        Index("ix_risk_signals_risk_level", "risk_level"),
        Index("ix_risk_signals_event_class", "event_class"),
        Index("ix_risk_signals_created_at", "created_at"),
    )


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(String(64), primary_key=True, default=new_uuid)
    name = Column(String(256), nullable=False)
    total_value = Column(Float, nullable=False)
    currency = Column(String(8), default="USD")
    description = Column(Text, nullable=True)
    is_synthetic = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    positions = relationship("PortfolioPosition", back_populates="portfolio")


class PortfolioPosition(Base):
    __tablename__ = "portfolio_positions"

    id = Column(String(64), primary_key=True, default=new_uuid)
    portfolio_id = Column(String(64), ForeignKey("portfolios.id"), nullable=False)
    asset_id = Column(String(64), nullable=False)
    asset_class = Column(String(64), nullable=False)
    issuer = Column(String(256), nullable=True)
    ticker = Column(String(16), nullable=True)
    notional = Column(Float, nullable=False)
    sector = Column(String(128), nullable=True)
    country = Column(String(64), nullable=True)
    duration = Column(Float, nullable=True)
    credit_quality = Column(String(32), nullable=True)
    risk_weight = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    portfolio = relationship("Portfolio", back_populates="positions")


class StressScenario(Base):
    __tablename__ = "stress_scenarios"

    id = Column(String(64), primary_key=True, default=new_uuid)
    name = Column(String(128), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    parameters = Column(JSON, nullable=False)
    assumptions = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class StressSimulation(Base):
    __tablename__ = "stress_simulations"

    id = Column(String(64), primary_key=True, default=new_uuid)
    trigger_signal_id = Column(String(64), ForeignKey("risk_signals.id"), nullable=True)
    scenario_name = Column(String(128), nullable=False)
    portfolio_id = Column(String(64), nullable=True)
    portfolio_before = Column(Float, nullable=False)
    portfolio_after = Column(Float, nullable=False)
    absolute_loss = Column(Float, nullable=False)
    loss_percentage = Column(Float, nullable=False)
    asset_level_impacts = Column(JSON, nullable=True)
    is_auto_triggered = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    trigger_signal = relationship("RiskSignal", back_populates="stress_simulations")

    __table_args__ = (
        Index("ix_stress_simulations_created_at", "created_at"),
    )
