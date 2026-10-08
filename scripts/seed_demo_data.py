"""
Seed demo data — runs the full pipeline with diverse demo events.

This populates the database with a representative set of events
so judges can see the system in action immediately.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

DEMO_EVENTS = [
    {
        "text": "Escalating geopolitical tensions disrupt critical energy supply routes, raising concerns over global inflation and corporate input costs.",
        "source_name": "Synthetic Demo Dataset",
        "source_type": "demo",
    },
    {
        "text": "Federal Reserve signals aggressive rate increases as inflation remains stubbornly above target, banks reassess credit risk exposure across portfolios.",
        "source_name": "Synthetic Demo Dataset",
        "source_type": "demo",
    },
    {
        "text": "Major technology company faces supply chain disruption after shipping delays worsen at critical Asian manufacturing facilities.",
        "source_name": "Synthetic Demo Dataset",
        "source_type": "demo",
    },
    {
        "text": "Credit rating agency downgrades several major financial institutions citing deteriorating asset quality and rising non-performing loan ratios.",
        "source_name": "Synthetic Demo Dataset",
        "source_type": "demo",
    },
    {
        "text": "Strong quarterly earnings from semiconductor sector drive market rally as AI demand continues to accelerate beyond analyst expectations.",
        "source_name": "Synthetic Demo Dataset",
        "source_type": "demo",
    },
]


def main() -> None:
    print("=" * 60)
    print("FinRisk Intelligence — Seeding Demo Data")
    print("=" * 60)

    from backend.app.core.database import SessionLocal
    from backend.app.services.risk.risk_fusion import RiskFusionService
    from backend.app.services.portfolio.portfolio_service import PortfolioService

    db = SessionLocal()
    risk_service = RiskFusionService()

    # Seed portfolio
    print("\nSeeding portfolio...")
    PortfolioService().seed_portfolio(db)

    # Process demo events
    print(f"\nProcessing {len(DEMO_EVENTS)} demo events...")
    for i, evt in enumerate(DEMO_EVENTS, 1):
        print(f"\n[{i}/{len(DEMO_EVENTS)}] Processing: {evt['text'][:60]}...")
        result = risk_service.analyze(
            text=evt["text"],
            source_name=evt["source_name"],
            source_type=evt["source_type"],
            db=db,
        )
        print(f"  Sentiment: {result['sentiment']['label']} ({result['sentiment']['score']:+.3f})")
        print(f"  Event: {result['event']['class']} ({result['event']['confidence']:.3f})")
        print(f"  Impact: {result['impact']['score']}/10 ({result['impact']['risk_level']})")
        print(f"  Time: {result['processing_time_ms']}ms")

    db.close()
    print("\n" + "=" * 60)
    print("Demo data seeded successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()
