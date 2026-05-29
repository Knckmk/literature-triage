from __future__ import annotations

import warnings
from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer


def _resolve_k(n_docs: int, requested_k: int) -> int:
    """Clamp the requested cluster count to a value KMeans can handle."""
    if n_docs < 1:
        raise ValueError("Cannot cluster an empty corpus.")
    k = max(1, int(requested_k))
    if k > n_docs:
        warnings.warn(
            f"Requested n_clusters={requested_k} > n_docs={n_docs}; clamping to {n_docs}.",
            stacklevel=2,
        )
        k = n_docs
    return k


def fit_kmeans(
    X: Any,
    n_clusters: int,
    random_state: int = 42,
    n_init: int = 10,
) -> tuple[KMeans, np.ndarray, np.ndarray]:
    """
    Fit KMeans on the document-term matrix.

    Returns the fitted model, the integer cluster labels for each document,
    and the Euclidean distance from each document to its assigned centroid
    (useful for ranking documents within a cluster).
    """
    n_docs = X.shape[0]
    k = _resolve_k(n_docs, n_clusters)

    model = KMeans(n_clusters=k, random_state=random_state, n_init=n_init)
    labels = model.fit_predict(X)

    distances_per_centroid = model.transform(X)
    own_distances = distances_per_centroid[np.arange(n_docs), labels]
    return model, labels.astype(int), own_distances.astype(float)


def top_keywords_per_cluster(
    vec: TfidfVectorizer,
    X: Any,
    labels: np.ndarray,
    top_k: int = 10,
) -> dict[int, list[str]]:
    """
    For every cluster, pick the top-``top_k`` terms by mean TF-IDF weight.

    Averaging the cluster members' rows highlights vocabulary that is dense
    across the cluster rather than terms that spike in a single document.
    """
    feature_names = np.array(vec.get_feature_names_out())
    keywords: dict[int, list[str]] = {}

    unique_labels = sorted({int(label) for label in labels})
    for label in unique_labels:
        mask = labels == label
        if not mask.any():
            keywords[label] = []
            continue
        sub = X[mask]
        mean_weights = np.asarray(sub.mean(axis=0)).ravel()
        if mean_weights.size == 0:
            keywords[label] = []
            continue
        top_idx = np.argsort(-mean_weights)[:top_k]
        keywords[label] = [
            feature_names[i] for i in top_idx if mean_weights[i] > 0.0
        ]
    return keywords
