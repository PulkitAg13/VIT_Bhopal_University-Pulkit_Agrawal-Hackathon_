import numpy as np
from app.core.model_manager import get_model_manager


def test_embedding_generation():
    mm = get_model_manager()
    vec = mm.get_embedding("Federal Reserve signals monetary tightening.")
    assert isinstance(vec, np.ndarray)
    assert len(vec) == 384
    # Check unit norm or reasonable magnitude
    norm = np.linalg.norm(vec)
    assert 0.95 <= norm <= 1.05


def test_embedding_cosine_similarity():
    mm = get_model_manager()
    v1 = mm.get_embedding("Federal Reserve raises interest rates.")
    v2 = mm.get_embedding("Central bank hikes benchmark borrowing costs.")
    v3 = mm.get_embedding("Apple launched a new iPhone with improved camera hardware.")

    sim_related = mm.cosine_similarity(v1, v2)
    sim_unrelated = mm.cosine_similarity(v1, v3)

    assert sim_related > sim_unrelated
    assert sim_related > 0.5
