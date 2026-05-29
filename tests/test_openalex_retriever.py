from __future__ import annotations

import json
from pathlib import Path

from retrievers.openalex_retriever import (
    parse_openalex_work,
    reconstruct_abstract,
    resolve_openalex_pdf_url,
)


def test_reconstruct_abstract():
    inverted = {"Hello": [0], "world": [1]}
    assert reconstruct_abstract(inverted) == "Hello world"


def test_parse_openalex_work_from_fixture():
    fixture = Path(__file__).parent / "fixtures" / "openalex_work.json"
    item = json.loads(fixture.read_text(encoding="utf-8"))

    paper = parse_openalex_work(item)

    assert paper.paper_id == "openalex:W123456789"
    assert paper.source == "openalex"
    assert paper.sources == ["openalex"]
    assert paper.title == "Distributed Minimum Spanning Tree Verification"
    assert "spanning tree verification" in paper.abstract.lower()
    assert paper.authors == ["Grace Hopper"]
    assert paper.year == 2024
    assert paper.doi == "10.1000/openalex.example"
    assert paper.citation_count == 17
    assert paper.pdf_url == "https://example.org/paper.pdf"


def test_resolve_pdf_from_best_oa_when_primary_has_none():
    item = {
        "primary_location": {"pdf_url": None},
        "best_oa_location": {"pdf_url": "https://repository.example.org/full.pdf"},
    }
    assert resolve_openalex_pdf_url(item) == "https://repository.example.org/full.pdf"


def test_resolve_pdf_from_open_access_oa_url():
    item = {
        "primary_location": {},
        "best_oa_location": {},
        "open_access": {
            "is_oa": True,
            "oa_url": "https://pmc.example.org/articles/PMC123/pdf/main.pdf",
        },
    }
    assert (
        resolve_openalex_pdf_url(item)
        == "https://pmc.example.org/articles/PMC123/pdf/main.pdf"
    )


def test_record_url_prefers_landing_page_over_openalex_id():
    item = {
        "id": "https://openalex.org/W999",
        "primary_location": {
            "landing_page_url": "https://publisher.example.org/article/1",
            "pdf_url": None,
        },
    }
    paper = parse_openalex_work(item)
    assert paper.url == "https://publisher.example.org/article/1"
