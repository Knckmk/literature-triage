from __future__ import annotations

from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer


def build_tfidf(docs_text: list[str]) -> tuple[TfidfVectorizer, Any]:
    """
    Build a document-level TF-IDF matrix.

    Returns the fitted ``TfidfVectorizer`` and a sparse document-term matrix
    (``scipy.sparse.csr_matrix``). The same fitted vectorizer is reused by
    ranking and clustering. Sentence-level scoring (``summarize.py``) builds
    its own lightweight vectorizer because short sentences need different
    parameters.
    """
    vec = TfidfVectorizer(
        stop_words="english",
        lowercase=True,
        max_features=50000,
        ngram_range=(1, 2),
        min_df=1,
    )
    X = vec.fit_transform(docs_text)
    return vec, X
