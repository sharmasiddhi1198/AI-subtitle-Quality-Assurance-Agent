from difflib import SequenceMatcher


def semantic_similarity(text1: str, text2: str) -> float:
    """
    Returns a lightweight text similarity score from 0 to 100.

    This version avoids loading Sentence Transformers and PyTorch,
    which keeps memory usage low enough for small cloud instances.
    """

    clean_text1 = " ".join(text1.lower().split())
    clean_text2 = " ".join(text2.lower().split())

    if not clean_text1 or not clean_text2:
        return 0.0

    similarity = SequenceMatcher(
        None,
        clean_text1,
        clean_text2,
    ).ratio()

    return round(similarity * 100, 2)