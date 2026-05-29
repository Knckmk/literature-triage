from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PaperMetadata:
    paper_id: str
    source: str
    title: str
    abstract: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    published: str | None = None
    updated: str | None = None
    url: str | None = None
    pdf_url: str | None = None
    doi: str | None = None
    venue: str | None = None
    citation_count: int | None = None
    fields_of_study: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)


@dataclass
class Document:
    doc_id: str
    title: str
    body: str
    path: str
    rel_path: str
    word_count: int
    metadata: PaperMetadata


@dataclass
class TriageResult:
    rank: int
    score: float
    document: Document
    cluster_id: int | None = None
    summary: list[str] = field(default_factory=list)
    snippet: str | None = None
