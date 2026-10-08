"""Pydantic schemas for API requests and responses."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Requests ─────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=5, max_length=5000)
    source_name: str = "manual"
    source_type: str = "manual"
    source_url: Optional[str] = None


class IngestRequest(BaseModel):
    source: str = Field(default="demo", description="Source type: demo, rss, dataset")
    ticker: str = Field(default="AAPL")
    dataset_name: str = Field(default="twitter_sentiment")
    max_items: int = Field(default=5, ge=1, le=50)


class StressTestRequest(BaseModel):
    scenario: str = "GEOPOLITICAL_SHOCK"
    portfolio_id: str = "wholesale-demo"


# ── Responses ────────────────────────────────────────────────

class SourceInfo(BaseModel):
    type: str
    name: str
    url: Optional[str] = None
    provider: Optional[str] = None
    domain: Optional[str] = None


class SentimentResult(BaseModel):
    label: str
    score: float
    confidence: float
    probabilities: Dict[str, float] = {}
    model: Optional[str] = None


class EventClassification(BaseModel):
    event_class: str = Field(alias="class")
    confidence: float
    model: Optional[str] = None

    class Config:
        populate_by_name = True


class ImpactResult(BaseModel):
    score: float
    risk_level: str
    components: Dict[str, float] = {}
    explanation: str = ""


class CorroborationResult(BaseModel):
    score: float
    independent_sources: int = 0
    independent_provider_count: int = 0
    independent_domains: List[str] = []
    similar_event_count: int = 0
    source_type_diversity: int = 1
    corroboration_score: float = 0.0


class EntityResult(BaseModel):
    canonical_name: str
    ticker: Optional[str] = None
    type: str
    confidence: float


class RiskSignalResponse(BaseModel):
    signal_id: str
    document_id: str
    timestamp: str
    source: SourceInfo
    text: str
    entities: List[EntityResult] = []
    sentiment: SentimentResult
    event: Dict[str, Any]
    impact: ImpactResult
    novelty_score: float
    corroboration: CorroborationResult
    confidence_score: float
    risk_trajectory: str
    explanation: List[str] = []
    stress_test: Dict[str, Any] = {}
    processing_time_ms: int = 0
    market_context_available: bool = False
    cluster_id: Optional[str] = None
    cluster_status: Optional[str] = None
    already_processed: Optional[bool] = False

    class Config:
        from_attributes = True


class EventListResponse(BaseModel):
    items: List[Dict[str, Any]]
    count: int
    page: int = 1
    page_size: int = 50


class EntityListItem(BaseModel):
    id: str
    canonical_name: str
    ticker: Optional[str] = None
    entity_type: str
    event_count: int = 0
    avg_risk: float = 0.0
    avg_sentiment: float = 0.0
    last_seen: Optional[str] = None


class EntityListResponse(BaseModel):
    items: List[EntityListItem]
    count: int


class EntityDetailResponse(BaseModel):
    entity: EntityListItem
    events: List[Dict[str, Any]] = []
    risk_timeline: List[Dict[str, Any]] = []
    sentiment_timeline: List[Dict[str, Any]] = []


class PortfolioResponse(BaseModel):
    portfolio_id: str
    name: str
    total_value: float
    is_synthetic: bool = True
    by_asset_class: List[Dict[str, Any]] = []
    by_sector: List[Dict[str, Any]] = []
    positions: List[Dict[str, Any]] = []


class StressScenarioInfo(BaseModel):
    name: str
    description: str = ""
    assumptions: str = ""
    parameters: Dict[str, float] = {}


class StressResultResponse(BaseModel):
    simulation_id: str
    scenario: str
    description: str = ""
    assumptions: str = ""
    trigger_signal_id: Optional[str] = None
    is_auto_triggered: bool = False
    portfolio_before: float
    portfolio_after: float
    absolute_loss: float
    loss_percentage: float
    asset_level_impacts: List[Dict[str, Any]] = []
    timestamp: str = ""


class HealthResponse(BaseModel):
    status: str
    service: str
    database: str
    redis: str
    models: Dict[str, str] = {}


class ReadinessResponse(BaseModel):
    status: str
    database: str
    redis: str
    models: Dict[str, str] = {}


class AnalyticsOverview(BaseModel):
    events_processed: int = 0
    high_risk_events: int = 0
    critical_events: int = 0
    average_sentiment: float = 0.0
    average_impact: float = 0.0
    overall_risk: float = 0.0
    market_risk: str = "LOW"
    event_distribution: Dict[str, int] = {}
    sentiment_distribution: Dict[str, int] = {}
    risk_distribution: Dict[str, int] = {}
    source_distribution: Dict[str, int] = {}


class IngestResponse(BaseModel):
    ingested: int
    source: str
    signals: List[Dict[str, Any]] = []


class DemoRunResponse(BaseModel):
    steps: List[Dict[str, Any]] = []
    demo_event: Dict[str, Any] = {}
    stress_test: Optional[Dict[str, Any]] = None
    success: bool = True
