from __future__ import annotations

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def rank_by_query(
    vec: TfidfVectorizer,
    X_docs,
    query: str,
) -> np.ndarray:
    """Return cosine similarity scores for each document against the query."""
    q = query.strip()
    if not q:
        return np.zeros(X_docs.shape[0], dtype=float)

    X_q = vec.transform([q])
    scores = cosine_similarity(X_docs, X_q).reshape(-1)
    return scores


def topn_indices(scores: np.ndarray, topn: int) -> list[int]:
    """Return indices of the top-N scores in descending order."""
    topn = max(1, int(topn))
    idx = np.argsort(-scores)
    return idx[:topn].tolist()
