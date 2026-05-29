from __future__ import annotations

from models import PaperMetadata
from retrievers.merge_corpora import merge_and_dedupe


def _paper(**kwargs) -> PaperMetadata:
    defaults = {
        "paper_id": "test:1",
        "source": "arxiv",
        "title": "Example Paper",
        "abstract": "one two three four five six",
        "authors": [],
        "sources": ["arxiv"],
    }
    defaults.update(kwargs)
    return PaperMetadata(**defaults)


def test_merge_same_doi():
    arxiv = _paper(
        paper_id="arxiv:2401.12345",
        source="arxiv",
        doi="10.1000/example",
        url="http://arxiv.org/abs/2401.12345",
        sources=["arxiv"],
    )
    openalex = _paper(
        paper_id="openalex:W1",
        source="openalex",
        doi="10.1000/example",
        abstract="one two three four five six seven eight",
        citation_count=10,
        pdf_url="https://example.org/paper.pdf",
        sources=["openalex"],
    )

    merged = merge_and_dedupe([arxiv, openalex])
    assert len(merged) == 1
    assert set(merged[0].sources) == {"arxiv", "openalex"}
    assert merged[0].citation_count == 10
    assert merged[0].pdf_url == "https://example.org/paper.pdf"


def test_drops_short_abstract():
    short = _paper(abstract="too short")
    long = _paper(paper_id="test:2", title="Other", abstract="one two three four five six")
    merged = merge_and_dedupe([short, long])
    assert len(merged) == 1
    assert merged[0].paper_id == "test:2"
