from app.services.nlp.entity_extractor import extract_entities


def test_entity_extraction_structure():
    entities = extract_entities("Apple Inc. reported record services revenue while Microsoft shares traded higher.")
    assert isinstance(entities, list)
    if entities:
        ent = entities[0]
        assert "canonical_name" in ent
        assert "type" in ent
        assert "confidence" in ent


def test_entity_extraction_known_companies():
    entities = extract_entities("JPMorgan Chase expanded loans as Apple and NVIDIA announced new AI silicon partnerships.")
    names = [e["canonical_name"].lower() for e in entities]
    tickers = [e.get("ticker") for e in entities if e.get("ticker")]
    assert any("apple" in n or "jpmorgan" in n or "nvidia" in n for n in names) or len(tickers) > 0
