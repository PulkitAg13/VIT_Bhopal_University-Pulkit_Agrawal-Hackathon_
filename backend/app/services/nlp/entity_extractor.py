"""Real entity extraction using dictionary + regex pattern matching.

Uses config/entities.yaml as resolution layer plus regex patterns
for ticker symbols, organizations, and financial entities.
"""
from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import Any, Dict, List

import yaml

logger = logging.getLogger("finrisk.nlp.entities")

_CONFIG_PATH = Path(__file__).resolve().parents[4] / "config" / "entities.yaml"

# Load entity resolution table from config
_ENTITY_MAP: Dict[str, Dict[str, Any]] = {}
_ALIASES: Dict[str, str] = {}


def _load_config() -> None:
    global _ENTITY_MAP, _ALIASES
    if _ENTITY_MAP:
        return
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh)
        for entry in cfg.get("entities", []):
            name = entry["name"]
            _ENTITY_MAP[name.lower()] = {
                "canonical_name": name,
                "ticker": entry.get("ticker"),
                "type": entry.get("type", "company"),
            }
            if entry.get("ticker"):
                _ALIASES[entry["ticker"].upper()] = name.lower()

    # Additional aliases for common mentions
    extra_aliases = {
        "apple": "apple inc.",
        "google": "alphabet inc.",
        "alphabet": "alphabet inc.",
        "jpmorgan": "jpmorgan chase",
        "jp morgan": "jpmorgan chase",
        "bofa": "bank of america",
        "the fed": "federal reserve",
        "us federal reserve": "federal reserve",
        "federal reserve": "federal reserve",
        "oil": "crude oil",
    }
    for alias, canonical in extra_aliases.items():
        if canonical in _ENTITY_MAP:
            _ALIASES[alias] = canonical


_load_config()


# Regex for common financial entities
_ORG_PATTERNS = [
    r"\b(Apple|Microsoft|NVIDIA|Tesla|Amazon|Meta|Google|Alphabet)\b",
    r"\b(JPMorgan|Bank of America|Goldman Sachs|Morgan Stanley|Citigroup)\b",
    r"\b(Federal Reserve|Fed|ECB|Bank of England|BOJ)\b",
    r"\b(SEC|CFTC|OCC|FINRA|FDIC)\b",
]

_TICKER_PATTERN = re.compile(r"\b([A-Z]{1,5})\b")
_KNOWN_TICKERS = {"AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META", "GOOGL", "JPM", "BAC",
                   "GS", "MS", "C", "WFC", "XOM", "CVX", "V", "MA"}

_COMMODITY_PATTERN = re.compile(r"\b(oil|crude|gold|silver|natural gas|copper|wheat|corn)\b", re.IGNORECASE)
_CURRENCY_PATTERN = re.compile(r"\b(US dollar|USD|euro|EUR|yen|JPY|pound|GBP|yuan|CNY)\b", re.IGNORECASE)
_COUNTRY_PATTERN = re.compile(
    r"\b(United States|US|UK|China|Japan|Germany|France|India|Russia|Brazil|"
    r"Eurozone|European Union|EU)\b", re.IGNORECASE
)

COMMODITY_MAP = {
    "oil": {"canonical_name": "Crude Oil", "ticker": "CL=F", "type": "commodity"},
    "crude": {"canonical_name": "Crude Oil", "ticker": "CL=F", "type": "commodity"},
    "gold": {"canonical_name": "Gold", "ticker": "GC=F", "type": "commodity"},
    "silver": {"canonical_name": "Silver", "ticker": "SI=F", "type": "commodity"},
    "natural gas": {"canonical_name": "Natural Gas", "ticker": "NG=F", "type": "commodity"},
    "copper": {"canonical_name": "Copper", "ticker": "HG=F", "type": "commodity"},
}

CURRENCY_MAP = {
    "us dollar": {"canonical_name": "US Dollar", "ticker": "USD", "type": "currency"},
    "usd": {"canonical_name": "US Dollar", "ticker": "USD", "type": "currency"},
    "euro": {"canonical_name": "Euro", "ticker": "EUR", "type": "currency"},
    "eur": {"canonical_name": "Euro", "ticker": "EUR", "type": "currency"},
    "yen": {"canonical_name": "Japanese Yen", "ticker": "JPY", "type": "currency"},
    "jpy": {"canonical_name": "Japanese Yen", "ticker": "JPY", "type": "currency"},
    "pound": {"canonical_name": "British Pound", "ticker": "GBP", "type": "currency"},
    "gbp": {"canonical_name": "British Pound", "ticker": "GBP", "type": "currency"},
}


def extract_entities(text: str) -> List[Dict[str, Any]]:
    """Extract and resolve entities from financial text."""
    found: List[Dict[str, Any]] = []
    seen_names: set = set()

    def _add(canonical_name: str, ticker: str | None, entity_type: str, confidence: float) -> None:
        if canonical_name in seen_names:
            return
        seen_names.add(canonical_name)
        found.append({
            "canonical_name": canonical_name,
            "ticker": ticker,
            "type": entity_type,
            "confidence": round(confidence, 4),
        })

    lowered = text.lower()

    # 1. Match against config entity map (dictionary resolution)
    for key, details in _ENTITY_MAP.items():
        if key in lowered:
            _add(details["canonical_name"], details.get("ticker"), details["type"], 0.88)

    # 2. Check aliases
    for alias, canonical_key in _ALIASES.items():
        if alias.lower() in lowered and canonical_key in _ENTITY_MAP:
            details = _ENTITY_MAP[canonical_key]
            _add(details["canonical_name"], details.get("ticker"), details["type"], 0.85)

    # 3. Regex: ticker symbols
    for match in _TICKER_PATTERN.findall(text):
        if match in _KNOWN_TICKERS and match.upper() in _ALIASES:
            canonical_key = _ALIASES[match.upper()]
            if canonical_key in _ENTITY_MAP:
                details = _ENTITY_MAP[canonical_key]
                _add(details["canonical_name"], details.get("ticker"), details["type"], 0.90)

    # 4. Regex: organizations
    for pattern in _ORG_PATTERNS:
        for match in re.findall(pattern, text, re.IGNORECASE):
            name_lower = match.lower()
            resolved = _ALIASES.get(name_lower) or name_lower
            if resolved in _ENTITY_MAP:
                details = _ENTITY_MAP[resolved]
                _add(details["canonical_name"], details.get("ticker"), details["type"], 0.85)
            else:
                _add(match, None, "organization", 0.70)

    # 5. Commodities
    for match in _COMMODITY_PATTERN.findall(text):
        key = match.lower()
        if key in COMMODITY_MAP:
            c = COMMODITY_MAP[key]
            _add(c["canonical_name"], c["ticker"], c["type"], 0.82)

    # 6. Currencies
    for match in _CURRENCY_PATTERN.findall(text):
        key = match.lower()
        if key in CURRENCY_MAP:
            c = CURRENCY_MAP[key]
            _add(c["canonical_name"], c["ticker"], c["type"], 0.80)

    # 7. Countries/Regions
    for match in _COUNTRY_PATTERN.findall(text):
        _add(match, None, "region", 0.75)

    # Fallback if nothing found
    if not found:
        _add("General Market", None, "macro", 0.45)

    return found
