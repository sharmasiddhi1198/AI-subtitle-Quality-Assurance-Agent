from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim

MODEL_NAME = "all-MiniLM-L6-v2"

_model = None


def get_model():
    global _model

    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)

    return _model


def semantic_similarity(text1: str, text2: str) -> float:
    """
    Returns semantic similarity between two sentences.
    Score is from 0 to 100.
    """

    if not text1.strip() or not text2.strip():
        return 0.0

    model = get_model()

    embeddings = model.encode(
        [text1, text2],
        convert_to_tensor=True
    )

    similarity = cos_sim(
        embeddings[0],
        embeddings[1]
    ).item()

    similarity = max(0.0, similarity)

    return round(similarity * 100, 2)