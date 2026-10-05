"""Entity extraction using transformer NER + financial entity resolution & enrichment.

Architecture:
    Raw text
     ↓
    Transformer NER (dslim/bert-base-NER) → ORG / LOC / MISC / PER
     ↓
    Financial entity resolver (config/entities.yaml + canonical mapping)
     ↓
    Dictionary/alias/regex enrichment (clearly labelled extraction methods)
     ↓
    Canonical financial entities

CRITICAL:
- No fabricated "General Market" fallback entity. If none found, returns [].
- If transformer NER is unavailable, it is marked as unavailable and secondary
  dictionary/pattern layers are labelled accurately (not claimed as NER).
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from app.core.model_manager import get_model_manager, READY

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
        try:
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
        except Exception as exc:
            logger.warning("Failed to load entities.yaml: %s", exc)

    # Additional aliases for financial mentions
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
        "exxonmobil": "exxonmobil",
        "exxon mobil": "exxonmobil",
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
    r"\b(ExxonMobil|Exxon Mobil|Chevron)\b",
    r"\b(Federal Reserve|Fed|ECB|Bank of England|BOJ)\b",
    r"\b(SEC|CFTC|OCC|FINRA|FDIC)\b",
]

_TICKER_PATTERN = re.compile(r"\b([A-Z]{1,5})\b")
_KNOWN_TICKERS = {
    "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META", "GOOGL", "JPM", "BAC",
    "GS", "MS", "C", "WFC", "XOM", "CVX", "V", "MA",
}

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

_NER_TYPE_MAP = {
    "ORG": "organization",
    "PER": "person",
    "LOC": "region",
    "MISC": "other",
}


def _resolve_ner_entity(word: str, entity_group: str) -> Optional[Dict[str, Any]]:
    """Resolve a NER-extracted entity to a canonical financial entity."""
    lowered = word.lower().strip()

    # Check direct match in entity map
    if lowered in _ENTITY_MAP:
        details = _ENTITY_MAP[lowered]
        return {
            "canonical_name": details["canonical_name"],
            "ticker": details.get("ticker"),
            "type": details["type"],
            "confidence": 0.92,
            "extraction_method": "transformer_ner+canonical_resolution",
        }

    # Check aliases
    if lowered in _ALIASES:
        canonical_key = _ALIASES[lowered]
        if canonical_key in _ENTITY_MAP:
            details = _ENTITY_MAP[canonical_key]
            return {
                "canonical_name": details["canonical_name"],
                "ticker": details.get("ticker"),
                "type": details["type"],
                "confidence": 0.90,
                "extraction_method": "transformer_ner+alias_resolution",
            }

    # Check known ticker
    if word.upper() in _ALIASES:
        canonical_key = _ALIASES[word.upper()]
        if canonical_key in _ENTITY_MAP:
            details = _ENTITY_MAP[canonical_key]
            return {
                "canonical_name": details["canonical_name"],
                "ticker": details.get("ticker"),
                "type": details["type"],
                "confidence": 0.90,
                "extraction_method": "transformer_ner+ticker_resolution",
            }

    # Unresolved NER entity — preserve with mapped type
    ent_type = _NER_TYPE_MAP.get(entity_group, "organization")
    return {
        "canonical_name": word.strip(),
        "ticker": None,
        "type": ent_type,
        "confidence": 0.70,
        "extraction_method": "transformer_ner",
    }


def extract_entities(text: str) -> List[Dict[str, Any]]:
    """Extract and resolve entities from financial text.

    Architecture:
    1. Transformer NER model (bert-base-NER) as primary extraction stage.
    2. Financial entity resolver mapping NER tokens to canonical entities.
    3. Dictionary / alias / regex enrichment as clearly-labelled secondary layers.

    CRITICAL:
    - Never fabricates 'General Market'. Returns [] if no entities found.
    - If transformer NER model is unavailable, secondary methods are explicitly
      labelled as 'dictionary' or 'regex', and never claimed as transformer NER.
    """
    found: List[Dict[str, Any]] = []
    seen_names: set[str] = set()

    def _add(
        canonical_name: str,
        ticker: Optional[str],
        entity_type: str,
        confidence: float,
        method: str,
    ) -> None:
        c_clean = canonical_name.strip()
        if not c_clean or c_clean.lower() in seen_names:
            return
        seen_names.add(c_clean.lower())
        found.append({
            "canonical_name": c_clean,
            "ticker": ticker,
            "type": entity_type,
            "confidence": round(confidence, 4),
            "extraction_method": method,
        })

    # ── Stage 1: Transformer NER ─────────────────────────
    mm = get_model_manager()
    ner_results = mm.extract_ner(text)

    for ner_ent in ner_results:
        word = ner_ent["word"].replace("##", "").strip()
        if len(word) < 2:
            continue
        resolved = _resolve_ner_entity(word, ner_ent.get("entity_group", "ORG"))
        if resolved:
            _add(
                resolved["canonical_name"],
                resolved.get("ticker"),
                resolved["type"],
                resolved["confidence"],
                resolved.get("extraction_method", "transformer_ner"),
            )

    # ── Stage 2: Dictionary enrichment (clearly labelled) ──
    lowered = text.lower()

    for key, details in _ENTITY_MAP.items():
        if key in lowered:
            _add(
                details["canonical_name"],
                details.get("ticker"),
                details["type"],
                0.85,
                "dictionary_enrichment",
            )

    for alias, canonical_key in _ALIASES.items():
        if alias.lower() in lowered and canonical_key in _ENTITY_MAP:
            details = _ENTITY_MAP[canonical_key]
            _add(
                details["canonical_name"],
                details.get("ticker"),
                details["type"],
                0.82,
                "alias_enrichment",
            )

    # ── Stage 3: Regex / Pattern enrichment ────────────────
    # Ticker symbols
    for match in _TICKER_PATTERN.findall(text):
        if match in _KNOWN_TICKERS and match.upper() in _ALIASES:
            canonical_key = _ALIASES[match.upper()]
            if canonical_key in _ENTITY_MAP:
                details = _ENTITY_MAP[canonical_key]
                _add(
                    details["canonical_name"],
                    details.get("ticker"),
                    details["type"],
                    0.88,
                    "ticker_pattern",
                )

    # Known organizations pattern
    for pattern in _ORG_PATTERNS:
        for match in re.findall(pattern, text, re.IGNORECASE):
            name_lower = match.lower()
            resolved = _ALIASES.get(name_lower) or name_lower
            if resolved in _ENTITY_MAP:
                details = _ENTITY_MAP[resolved]
                _add(
                    details["canonical_name"],
                    details.get("ticker"),
                    details["type"],
                    0.82,
                    "regex_enrichment",
                )
            else:
                _add(match, None, "organization", 0.68, "regex_enrichment")

    # Commodities
    for match in _COMMODITY_PATTERN.findall(text):
        key = match.lower()
        if key in COMMODITY_MAP:
            c = COMMODITY_MAP[key]
            _add(c["canonical_name"], c["ticker"], c["type"], 0.80, "commodity_pattern")

    # Currencies
    for match in _CURRENCY_PATTERN.findall(text):
        key = match.lower()
        if key in CURRENCY_MAP:
            c = CURRENCY_MAP[key]
            _add(c["canonical_name"], c["ticker"], c["type"], 0.78, "currency_pattern")

    # Countries/Regions
    for match in _COUNTRY_PATTERN.findall(text):
        _add(match, None, "region", 0.72, "region_pattern")

    # CRITICAL: If no entity exists, return [] (NEVER fabricated "General Market")
    return found
