from __future__ import annotations

import re
from typing import Any

from utils import split_sentences

_TOKEN_RE = re.compile(r"\b[a-zA-Z][a-zA-Z0-9_-]*\b")


def extract_query_terms(query: str) -> list[str]:
    """Return normalized, de-duplicated query terms in query order."""
    terms: list[str] = []
    seen: set[str] = set()
    for match in _TOKEN_RE.finditer(query.lower()):
        term = match.group(0).strip("_-")
        if not term or term in seen:
            continue
        seen.add(term)
        terms.append(term)
    return terms


def matched_terms(query: str, text: str) -> list[str]:
    """Return query terms that appear in ``text``, case-insensitively."""
    if not text:
        return []

    out: list[str] = []
    lowered_text = text.lower()
    for term in extract_query_terms(query):
        pattern = rf"(?<![a-zA-Z0-9_-]){re.escape(term)}(?![a-zA-Z0-9_-])"
        if re.search(pattern, lowered_text):
            out.append(term)
    return out


def top_weighted_terms_for_doc(
    vec: Any,
    X: Any,
    doc_index: int,
    top_k: int = 10,
) -> list[str]:
    """Return the highest-weight TF-IDF terms for one document row."""
    top_k = max(1, int(top_k))
    row = X[doc_index]
    feature_names = vec.get_feature_names_out()

    if not hasattr(row, "tocoo"):
        weights = list(enumerate(row))
    else:
        coo = row.tocoo()
        weights = list(zip(coo.col.tolist(), coo.data.tolist()))

    ranked = sorted(
        ((int(idx), float(weight)) for idx, weight in weights if float(weight) > 0.0),
        key=lambda item: (-item[1], feature_names[item[0]]),
    )
    return [str(feature_names[idx]) for idx, _ in ranked[:top_k]]


def best_matching_sentences(text: str, query: str, n: int = 3) -> list[str]:
    """
    Return the best matching sentences in relevance order.

    Scoring is deterministic and based on query-term overlap:
    unique matched terms first, then total occurrences, then original order.
    """
    n = max(1, int(n))
    sentences = split_sentences(text)
    if not sentences:
        return []

    terms = extract_query_terms(query)
    if not terms:
        return sentences[:n]

    scored: list[tuple[int, int, int, str]] = []
    for idx, sentence in enumerate(sentences):
        lowered = sentence.lower()
        unique_hits = 0
        total_hits = 0
        for term in terms:
            pattern = rf"(?<![a-zA-Z0-9_-]){re.escape(term)}(?![a-zA-Z0-9_-])"
            hits = len(re.findall(pattern, lowered))
            if hits:
                unique_hits += 1
                total_hits += hits
        scored.append((unique_hits, total_hits, idx, sentence))

    if not any(unique_hits > 0 for unique_hits, _, _, _ in scored):
        return sentences[:n]

    ranked = sorted(scored, key=lambda item: (-item[0], -item[1], item[2]))
    return [sentence for _, _, _, sentence in ranked[:n]]
