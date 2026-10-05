"""Test embedding generation and cosine similarity."""
import numpy as np
from app.core.model_manager import get_model_manager


def test_embedding_generation():
    mm = get_model_manager()
    vecs = mm.encode(["Federal Reserve signals monetary tightening."])
    assert isinstance(vecs, np.ndarray)
    assert vecs.shape[0] == 1
    assert vecs.shape[1] == 384
    vec = vecs[0]
    # Check reasonable magnitude
    norm = np.linalg.norm(vec)
    assert norm > 0.5


def test_embedding_cosine_similarity():
    mm = get_model_manager()
    v1 = mm.encode(["Federal Reserve raises interest rates."])[0]
    v2 = mm.encode(["Central bank hikes benchmark borrowing costs."])[0]
    v3 = mm.encode(["Apple launched a new iPhone with improved camera hardware."])[0]

    sim_related = mm.cosine_similarity(v1, v2)
    sim_unrelated = mm.cosine_similarity(v1, v3)

    assert sim_related > sim_unrelated
    assert sim_related > 0.5
