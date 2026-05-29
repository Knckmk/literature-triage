from __future__ import annotations

from pathlib import Path

from retrievers.arxiv_retriever import parse_arxiv_entry


def test_parse_arxiv_entry_from_fixture():
    fixture = Path(__file__).parent / "fixtures" / "arxiv_entry.xml"

    paper = parse_arxiv_entry(fixture.read_text(encoding="utf-8"))

    assert paper.paper_id == "arxiv:2401.12345"
    assert paper.source == "arxiv"
    assert paper.sources == ["arxiv"]
    assert paper.title == "Graphic TSP Approximation with Parity Correction"
    assert "parity correction" in paper.abstract
    assert paper.authors == ["Ada Lovelace", "Alan Turing"]
    assert paper.year == 2024
    assert paper.published == "2024-01-15T09:00:00Z"
    assert paper.updated == "2024-02-03T12:34:56Z"
    assert paper.categories == ["cs.DS", "math.CO"]
    assert paper.url == "http://arxiv.org/abs/2401.12345v2"
    assert paper.pdf_url == "http://arxiv.org/pdf/2401.12345v2"
