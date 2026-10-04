"""API dependencies — database session and service instances."""
from __future__ import annotations

from app.services.risk.risk_fusion import RiskFusionService
from app.services.portfolio.portfolio_service import PortfolioService
from app.services.stress.stress_engine import StressEngine

risk_service = RiskFusionService()
portfolio_service = PortfolioService()
stress_engine = StressEngine()
