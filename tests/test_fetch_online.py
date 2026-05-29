from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import urllib.error

from models import PaperMetadata
from retrievers.fetch_online import (
    SOURCE_ARXIV,
    SOURCE_OPENALEX,
    VALID_SOURCES,
    fetch_online_corpus,
    format_partial_fetch_warning,
)


def _sample(source: str, paper_id: str, abstract: str) -> PaperMetadata:
    return PaperMetadata(
        paper_id=paper_id,
        source=source,
        title=f"Title {paper_id}",
        abstract=abstract,
        authors=["Author"],
        sources=[source],
    )


@patch("retrievers.fetch_online.search_openalex")
@patch("retrievers.fetch_online.search_arxiv")
def test_fetch_only_selected_sources(mock_arxiv, mock_openalex, tmp_path):
    mock_arxiv.return_value = [
        _sample(SOURCE_ARXIV, "arxiv:1", "one two three four five six seven")
    ]
    mock_openalex.return_value = [
        _sample(SOURCE_OPENALEX, "openalex:W1", "one two three four five six eight")
    ]

    out = tmp_path / "corpus.jsonl"
    summary = fetch_online_corpus(
        "distributed spanning tree",
        sources={SOURCE_ARXIV, SOURCE_OPENALEX},
        max_results_per_source=10,
        jsonl_path=out,
    )

    mock_arxiv.assert_called_once()
    mock_openalex.assert_called_once()
    assert summary.merged_count == 2
    assert summary.sources_succeeded == [SOURCE_ARXIV, SOURCE_OPENALEX]
    assert summary.source_errors == {}
    assert out.exists()


@patch("retrievers.fetch_online.search_openalex")
@patch("retrievers.fetch_online.search_arxiv")
def test_fetch_continues_when_one_source_fails(mock_arxiv, mock_openalex, tmp_path):
    mock_arxiv.return_value = [
        _sample(SOURCE_ARXIV, "arxiv:1", "one two three four five six seven")
    ]
    mock_openalex.side_effect = urllib.error.HTTPError(
        url="https://api.openalex.org/",
        code=429,
        msg="Too Many Requests",
        hdrs=None,
        fp=None,
    )

    out = tmp_path / "corpus.jsonl"
    summary = fetch_online_corpus(
        "distributed spanning tree",
        sources=VALID_SOURCES,
        max_results_per_source=10,
        jsonl_path=out,
    )

    assert summary.merged_count == 1
    assert SOURCE_OPENALEX in summary.source_errors
    assert "429" in summary.source_errors[SOURCE_OPENALEX]
    assert SOURCE_ARXIV in summary.sources_succeeded
    assert SOURCE_OPENALEX not in summary.sources_succeeded
    assert "OpenAlex" in format_partial_fetch_warning(summary)
    assert out.exists()


@patch("retrievers.fetch_online.search_openalex")
@patch("retrievers.fetch_online.search_arxiv")
def test_fetch_raises_when_all_sources_fail(mock_arxiv, mock_openalex, tmp_path):
    mock_arxiv.side_effect = TimeoutError("timed out")
    mock_openalex.side_effect = TimeoutError("timed out")

    out = tmp_path / "corpus.jsonl"
    try:
        fetch_online_corpus(
            "query",
            sources=VALID_SOURCES,
            max_results_per_source=10,
            jsonl_path=out,
        )
    except ValueError as exc:
        assert "No papers could be retrieved" in str(exc)
    else:
        raise AssertionError("expected ValueError")
