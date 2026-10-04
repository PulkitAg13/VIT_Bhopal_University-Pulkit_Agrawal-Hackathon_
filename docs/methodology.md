# Methodology

## Risk signal generation

The platform ingests text, extracts prominent entities, computes financial sentiment, maps the event to a taxonomy, estimates impact, and fuses corroboration to produce a final risk signal.

## Impact formula

The scoring logic is intentionally transparent and prototype-grade. The score is derived from a weighted combination of:

- sentiment magnitude
- event severity
- source credibility
- corroboration and novelty
- recency
- portfolio exposure
- market volatility

The normalized result is constrained to 1-10.

## Stress testing

The stress engine applies scenario-specific shocks to a synthetic wholesale banking portfolio. Each asset class reacts according to scenario assumptions.

## Caveat

This is a demonstration system for a hackathon and is not intended to replace actual banking or regulatory risk models.
