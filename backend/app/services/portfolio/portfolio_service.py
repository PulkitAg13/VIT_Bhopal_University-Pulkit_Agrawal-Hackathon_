"""
Portfolio Service — Manages the synthetic wholesale banking portfolio.

Creates a realistic set of positions with individual assets,
issuers, tickers, sectors, and credit qualities.
"""
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models import Portfolio, PortfolioPosition

logger = logging.getLogger("finrisk.portfolio")

_PORTFOLIO_PATH = Path(__file__).resolve().parents[4] / "data" / "synthetic" / "portfolio.json"

# Realistic synthetic wholesale banking portfolio
SYNTHETIC_PORTFOLIO = {
    "portfolio_id": "wholesale-demo",
    "name": "Synthetic Wholesale Banking Portfolio (Demo)",
    "total_value": 100_000_000,
    "currency": "USD",
    "is_synthetic": True,
    "positions": [
        # Corporate Loans — $30M
        {"asset_id": "CL-001", "asset_class": "Corporate Loans", "issuer": "Tech Sector Borrowers", "ticker": "TECH-LOAN", "notional": 10_000_000, "sector": "Technology", "country": "US", "duration": None, "credit_quality": "BBB+", "risk_weight": 0.75},
        {"asset_id": "CL-002", "asset_class": "Corporate Loans", "issuer": "Energy Sector Borrowers", "ticker": "ENRG-LOAN", "notional": 8_000_000, "sector": "Energy", "country": "US", "duration": None, "credit_quality": "BBB", "risk_weight": 0.85},
        {"asset_id": "CL-003", "asset_class": "Corporate Loans", "issuer": "Financial Sector Borrowers", "ticker": "FIN-LOAN", "notional": 7_000_000, "sector": "Financials", "country": "US", "duration": None, "credit_quality": "A-", "risk_weight": 0.65},
        {"asset_id": "CL-004", "asset_class": "Corporate Loans", "issuer": "Industrial Borrowers", "ticker": "IND-LOAN", "notional": 5_000_000, "sector": "Industrials", "country": "EU", "duration": None, "credit_quality": "BBB-", "risk_weight": 0.90},
        # Government Bonds — $20M
        {"asset_id": "GB-001", "asset_class": "Government Bonds", "issuer": "US Treasury", "ticker": "UST-10Y", "notional": 12_000_000, "sector": "Government", "country": "US", "duration": 7.2, "credit_quality": "AAA", "risk_weight": 0.0},
        {"asset_id": "GB-002", "asset_class": "Government Bonds", "issuer": "German Bund", "ticker": "BUND-5Y", "notional": 8_000_000, "sector": "Government", "country": "DE", "duration": 4.5, "credit_quality": "AAA", "risk_weight": 0.0},
        # Corporate Bonds — $15M
        {"asset_id": "CB-001", "asset_class": "Corporate Bonds", "issuer": "Apple Inc.", "ticker": "AAPL-BOND", "notional": 5_000_000, "sector": "Technology", "country": "US", "duration": 5.0, "credit_quality": "AA+", "risk_weight": 0.20},
        {"asset_id": "CB-002", "asset_class": "Corporate Bonds", "issuer": "JPMorgan Chase", "ticker": "JPM-BOND", "notional": 5_000_000, "sector": "Financials", "country": "US", "duration": 3.5, "credit_quality": "A+", "risk_weight": 0.35},
        {"asset_id": "CB-003", "asset_class": "Corporate Bonds", "issuer": "ExxonMobil", "ticker": "XOM-BOND", "notional": 5_000_000, "sector": "Energy", "country": "US", "duration": 6.0, "credit_quality": "AA-", "risk_weight": 0.25},
        # Equities — $20M
        {"asset_id": "EQ-001", "asset_class": "Equities", "issuer": "Apple Inc.", "ticker": "AAPL", "notional": 5_000_000, "sector": "Technology", "country": "US", "duration": None, "credit_quality": None, "risk_weight": 1.0},
        {"asset_id": "EQ-002", "asset_class": "Equities", "issuer": "NVIDIA", "ticker": "NVDA", "notional": 4_000_000, "sector": "Technology", "country": "US", "duration": None, "credit_quality": None, "risk_weight": 1.0},
        {"asset_id": "EQ-003", "asset_class": "Equities", "issuer": "JPMorgan Chase", "ticker": "JPM", "notional": 3_500_000, "sector": "Financials", "country": "US", "duration": None, "credit_quality": None, "risk_weight": 1.0},
        {"asset_id": "EQ-004", "asset_class": "Equities", "issuer": "ExxonMobil", "ticker": "XOM", "notional": 3_500_000, "sector": "Energy", "country": "US", "duration": None, "credit_quality": None, "risk_weight": 1.0},
        {"asset_id": "EQ-005", "asset_class": "Equities", "issuer": "Microsoft", "ticker": "MSFT", "notional": 4_000_000, "sector": "Technology", "country": "US", "duration": None, "credit_quality": None, "risk_weight": 1.0},
        # Derivatives — $10M
        {"asset_id": "DV-001", "asset_class": "Derivatives", "issuer": "Interest Rate Swaps", "ticker": "IRS-5Y", "notional": 5_000_000, "sector": "Rates", "country": "US", "duration": 5.0, "credit_quality": None, "risk_weight": 0.50},
        {"asset_id": "DV-002", "asset_class": "Derivatives", "issuer": "Credit Default Swaps", "ticker": "CDS-IG", "notional": 3_000_000, "sector": "Credit", "country": "US", "duration": 3.0, "credit_quality": None, "risk_weight": 0.60},
        {"asset_id": "DV-003", "asset_class": "Derivatives", "issuer": "Equity Options", "ticker": "SPX-PUT", "notional": 2_000_000, "sector": "Equity", "country": "US", "duration": None, "credit_quality": None, "risk_weight": 0.70},
        # Cash — $5M
        {"asset_id": "CASH-001", "asset_class": "Cash", "issuer": "Cash & Equivalents", "ticker": "CASH", "notional": 5_000_000, "sector": "Cash", "country": "US", "duration": 0, "credit_quality": "AAA", "risk_weight": 0.0},
    ],
}


class PortfolioService:
    """Manage portfolio data — loads from DB or falls back to synthetic."""

    def load_portfolio(self, db: Optional[Session] = None) -> Dict[str, Any]:
        """Load portfolio with positions."""
        if db is not None:
            portfolio = db.query(Portfolio).first()
            if portfolio:
                positions = db.query(PortfolioPosition).filter(
                    PortfolioPosition.portfolio_id == portfolio.id
                ).all()
                return {
                    "portfolio_id": portfolio.id,
                    "name": portfolio.name,
                    "total_value": portfolio.total_value,
                    "currency": portfolio.currency,
                    "is_synthetic": portfolio.is_synthetic,
                    "positions": [
                        {
                            "asset_id": p.asset_id,
                            "asset_class": p.asset_class,
                            "issuer": p.issuer,
                            "ticker": p.ticker,
                            "notional": p.notional,
                            "sector": p.sector,
                            "country": p.country,
                            "duration": p.duration,
                            "credit_quality": p.credit_quality,
                            "risk_weight": p.risk_weight,
                        }
                        for p in positions
                    ],
                }
        return self._load_from_file()

    def _load_from_file(self) -> Dict[str, Any]:
        """Load from JSON file or return default."""
        if _PORTFOLIO_PATH.exists():
            try:
                with open(_PORTFOLIO_PATH, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if data.get("positions"):
                    return data
            except Exception:
                pass
        return SYNTHETIC_PORTFOLIO

    def seed_portfolio(self, db: Session) -> None:
        """Seed the synthetic portfolio into the database."""
        existing = db.query(Portfolio).filter(Portfolio.id == "wholesale-demo").first()
        if existing:
            return

        portfolio = Portfolio(
            id="wholesale-demo",
            name=SYNTHETIC_PORTFOLIO["name"],
            total_value=SYNTHETIC_PORTFOLIO["total_value"],
            currency="USD",
            description="Synthetic wholesale banking portfolio for demonstration purposes",
            is_synthetic=True,
        )
        db.add(portfolio)

        for pos in SYNTHETIC_PORTFOLIO["positions"]:
            pp = PortfolioPosition(
                id=str(uuid.uuid4()),
                portfolio_id="wholesale-demo",
                asset_id=pos["asset_id"],
                asset_class=pos["asset_class"],
                issuer=pos.get("issuer", ""),
                ticker=pos.get("ticker"),
                notional=pos["notional"],
                sector=pos.get("sector"),
                country=pos.get("country"),
                duration=pos.get("duration"),
                credit_quality=pos.get("credit_quality"),
                risk_weight=pos.get("risk_weight", 1.0),
            )
            db.add(pp)

        db.commit()
        logger.info("Seeded synthetic portfolio with %d positions", len(SYNTHETIC_PORTFOLIO["positions"]))

    def get_exposure(self, db: Optional[Session] = None) -> Dict[str, Any]:
        """Calculate portfolio exposure by asset class."""
        portfolio = self.load_portfolio(db)
        positions = portfolio.get("positions", [])
        total = portfolio.get("total_value", 0)

        # Group by asset class
        class_totals: Dict[str, float] = {}
        for pos in positions:
            ac = pos.get("asset_class", "Unknown")
            class_totals[ac] = class_totals.get(ac, 0) + pos.get("notional", pos.get("value", 0))

        exposures = []
        for ac, value in class_totals.items():
            exposures.append({
                "asset_class": ac,
                "value": value,
                "weight": round((value / total) * 100, 2) if total else 0,
            })

        # Group by sector
        sector_totals: Dict[str, float] = {}
        for pos in positions:
            sector = pos.get("sector", "Unknown")
            sector_totals[sector] = sector_totals.get(sector, 0) + pos.get("notional", pos.get("value", 0))

        sectors = []
        for sec, value in sector_totals.items():
            sectors.append({
                "sector": sec,
                "value": value,
                "weight": round((value / total) * 100, 2) if total else 0,
            })

        return {
            "portfolio_id": portfolio.get("portfolio_id", "default"),
            "name": portfolio.get("name", ""),
            "total_value": total,
            "is_synthetic": portfolio.get("is_synthetic", True),
            "by_asset_class": sorted(exposures, key=lambda x: x["value"], reverse=True),
            "by_sector": sorted(sectors, key=lambda x: x["value"], reverse=True),
            "positions": positions,
        }
