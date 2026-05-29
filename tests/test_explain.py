from __future__ import annotations

from explain import best_matching_sentences, matched_terms


def test_matched_terms_detects_case_insensitive_matches():
    terms = matched_terms(
        "Graphic TSP parity",
        "This paper studies graphic algorithms for the TSP problem.",
    )

    assert terms == ["graphic", "tsp"]


def test_best_matching_sentences_returns_relevant_sentence_first():
    text = (
        "This sentence is about unrelated background. "
        "Parity correction improves graphic TSP approximation algorithms. "
        "Approximation methods are discussed briefly."
    )

    snippets = best_matching_sentences(text, "graphic TSP parity correction", n=2)

    assert snippets[0] == "Parity correction improves graphic TSP approximation algorithms."
