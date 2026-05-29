from __future__ import annotations

import re


def generate_cluster_label(keywords: list[str], *, max_terms: int = 3) -> str:
    """
    Build a short label from this cluster's top TF-IDF keywords.

    Example: ["rigid", "packing", "spanning"] -> "Rigid / Packing / Spanning"
    """
    return _keyword_label(keywords, max_terms=max_terms)


def assign_cluster_labels(keywords_by_cluster: dict[int, list[str]]) -> dict[int, str]:
    """
    Assign a unique label per cluster using top keywords.

    If two clusters would share the same label, use more keywords or append
    the cluster id.
    """
    labels: dict[int, str] = {}
    used_labels: set[str] = set()
    for cid in sorted(keywords_by_cluster):
        keywords = keywords_by_cluster[cid]
        chosen = ""
        for n_terms in (3, 4, 5):
            candidate = generate_cluster_label(keywords, max_terms=n_terms)
            if candidate and candidate not in used_labels:
                chosen = candidate
                break
        if not chosen:
            base = generate_cluster_label(keywords)
            chosen = f"{base} ({cid})" if base else f"Cluster {cid}"
        labels[cid] = chosen
        used_labels.add(chosen)
    return labels


def _keyword_label(keywords: list[str], *, max_terms: int) -> str:
    picked: list[str] = []
    seen: set[str] = set()
    for keyword in keywords:
        cleaned = _display_keyword(keyword)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        picked.append(cleaned)
        if len(picked) >= max_terms:
            break
    return " / ".join(picked) if picked else "Unlabeled Cluster"


def _normalize_keyword(keyword: str) -> str:
    return re.sub(r"\s+", " ", keyword.strip().lower())


def _display_keyword(keyword: str) -> str:
    normalized = _normalize_keyword(keyword)
    if not normalized:
        return ""
    if normalized.upper() in {"LP", "TSP", "ATSP", "KKT", "2ECSS"}:
        return normalized.upper()
    return " ".join(
        part.upper() if part in {"lp", "tsp", "atsp", "kkt", "2ecss"} else part.title()
        for part in normalized.split()
    )
