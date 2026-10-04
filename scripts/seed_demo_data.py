from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "sample" / "demo_events.json"
SAMPLE.parent.mkdir(parents=True, exist_ok=True)

payload = {
    "events": [
        {
            "text": "Escalating geopolitical tensions disrupt critical energy supply routes, raising concerns over global inflation and corporate input costs.",
            "source": "Yahoo Finance RSS",
            "kind": "rss",
        },
        {
            "text": "Fed signals aggressive rate increases as inflation remains stubborn and banks reassess credit risk exposure.",
            "source": "Reuters",
            "kind": "rss",
        },
        {
            "text": "Apple's supplier network faces supply chain disruption after shipping delays worsen in major Asian ports.",
            "source": "Bloomberg",
            "kind": "rss",
        },
    ]
}
SAMPLE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print("Demo data seeded.")
