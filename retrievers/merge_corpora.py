from __future__ import annotations

import re
from dataclasses import replace

from models import PaperMetadata

MIN_ABSTRACT_WORDS = 5

DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s]+", re.IGNORECASE)
ARXIV_ID_PATTERN = re.compile(
    r"arxiv[:\s]*([0-9]{4}\.[0-9]{4,5}(?:v\d+)?|[a-z\-]+/[0-9]{7}(?:v\d+)?)",
    re.IGNORECASE,
)


def merge_and_dedupe(papers: list[PaperMetadata]) -> list[PaperMetadata]:
    """Merge duplicate papers and drop records without enough abstract text."""
    merged: dict[str, PaperMetadata] = {}
    key_order: list[str] = []

    for paper in papers:
        if _word_count(paper.abstract) < MIN_ABSTRACT_WORDS:
            continue
        key = _identity_key(paper)
        if key in merged:
            merged[key] = _merge_papers(merged[key], paper)
        else:
            merged[key] = _normalize_paper(paper)
            key_order.append(key)

    return [merged[key] for key in key_order]


def _normalize_paper(paper: PaperMetadata) -> PaperMetadata:
    sources = list(paper.sources) if paper.sources else []
    if paper.source and paper.source not in sources:
        sources.insert(0, paper.source)
    if not sources and paper.source:
        sources = [paper.source]
    return replace(paper, sources=sources)


def _merge_papers(left: PaperMetadata, right: PaperMetadata) -> PaperMetadata:
    left = _normalize_paper(left)
    right = _normalize_paper(right)

    abstract = left.abstract
    if _word_count(right.abstract) > _word_count(abstract):
        abstract = right.abstract

    citation_count = left.citation_count
    if right.citation_count is not None:
        if citation_count is None or right.citation_count > citation_count:
            citation_count = right.citation_count

    sources = []
    for src in list(left.sources) + list(right.sources):
        if src and src not in sources:
            sources.append(src)

    url = left.url or right.url
    pdf_url = left.pdf_url or right.pdf_url
    if right.source == "arxiv" or "arxiv" in right.sources:
        url = right.url or url
        pdf_url = right.pdf_url or pdf_url

    return PaperMetadata(
        paper_id=left.paper_id,
        source=left.source,
        title=left.title or right.title,
        abstract=abstract,
        authors=_union_strings(left.authors, right.authors),
        year=left.year or right.year,
        published=left.published or right.published,
        updated=left.updated or right.updated,
        url=url,
        pdf_url=pdf_url,
        doi=left.doi or right.doi,
        venue=left.venue or right.venue,
        citation_count=citation_count,
        fields_of_study=_union_strings(left.fields_of_study, right.fields_of_study),
        categories=_union_strings(left.categories, right.categories),
        sources=sources,
    )


def _identity_key(paper: PaperMetadata) -> str:
    doi = _normalize_doi(paper.doi)
    if doi:
        return f"doi:{doi}"

    arxiv_id = _extract_arxiv_id(paper.paper_id, paper.url, paper.pdf_url)
    if arxiv_id:
        return f"arxiv:{arxiv_id}"

    if paper.paper_id.startswith("openalex:"):
        return paper.paper_id

    title = _normalize_title(paper.title)
    if title:
        return f"title:{title}"

    return paper.paper_id or "unknown"


def _normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip().lower()
    text = text.replace("https://doi.org/", "")
    match = DOI_PATTERN.search(text)
    return match.group(0).lower() if match else text or None


def _extract_arxiv_id(*values: str | None) -> str | None:
    for value in values:
        if not value:
            continue
        match = ARXIV_ID_PATTERN.search(str(value))
        if match:
            return re.sub(r"v\d+$", "", match.group(1)).lower()
    return None


def _normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", (title or "").strip().lower())


def _union_strings(left: list[str], right: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in list(left) + list(right):
        text = str(value).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text or ""))
