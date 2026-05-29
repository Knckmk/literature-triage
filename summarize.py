from __future__ import annotations

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from utils import split_sentences

SNIPPET_CHARS = 600


def _build_sentence_vectorizer() -> TfidfVectorizer:
    """
    Vectorizer tuned for short sentences.

    Sentences are usually too short for bigrams to be reliable, so we drop
    them and lower ``min_df`` to 1. We rebuild the vocabulary per document
    because the relevant vocabulary differs from doc to doc.
    """
    return TfidfVectorizer(
        stop_words="english",
        lowercase=True,
        ngram_range=(1, 1),
        min_df=1,
    )


def query_focused_summary(
    body: str,
    query: str,
    n_sentences: int = 3,
) -> list[str]:
    """
    Return the top ``n_sentences`` body sentences ranked by similarity to the
    query, preserving the original sentence order in the returned list.

    If no usable sentences score above zero (for example the body shares no
    vocabulary with the query), fall back to the first ``n_sentences`` so
    the user still sees an intro snippet.
    """
    n_sentences = max(1, int(n_sentences))
    sentences = split_sentences(body)
    if not sentences:
        return []

    if len(sentences) <= n_sentences:
        return sentences

    if not query.strip():
        return sentences[:n_sentences]

    vec = _build_sentence_vectorizer()
    try:
        sent_matrix = vec.fit_transform(sentences)
        q_vec = vec.transform([query])
    except ValueError:
        return sentences[:n_sentences]

    scores = cosine_similarity(sent_matrix, q_vec).ravel()
    if not np.any(scores > 0.0):
        return sentences[:n_sentences]

    top_idx = np.argsort(-scores)[:n_sentences]
    chosen = sorted(int(i) for i in top_idx)
    return [sentences[i] for i in chosen]


def make_snippet(body: str, max_chars: int = SNIPPET_CHARS) -> str:
    """Return the first ~``max_chars`` characters of the body, trimmed cleanly."""
    flat = " ".join(body.split())
    if len(flat) <= max_chars:
        return flat
    cut = flat[:max_chars]
    last_space = cut.rfind(" ")
    if last_space > int(max_chars * 0.6):
        cut = cut[:last_space]
    return cut.rstrip() + "..."
