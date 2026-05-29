from __future__ import annotations

from models import PaperMetadata
from storage.jsonl_store import read_jsonl, write_jsonl


def test_jsonl_store_round_trip(tmp_path):
    path = tmp_path / "papers.jsonl"
    records = [
        PaperMetadata(
            paper_id="arxiv:2401.12345",
            source="arxiv",
            title="A Paper",
            abstract="An abstract.",
            authors=["Ada Lovelace"],
            year=2024,
            published="2024-01-15T09:00:00Z",
            updated="2024-02-03T12:34:56Z",
            url="http://arxiv.org/abs/2401.12345",
            pdf_url="http://arxiv.org/pdf/2401.12345",
            categories=["cs.DS"],
        )
    ]

    write_jsonl(path, records)
    loaded = read_jsonl(path)

    assert loaded == records
