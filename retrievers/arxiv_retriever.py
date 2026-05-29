from __future__ import annotations

import re
import urllib.parse
import xml.etree.ElementTree as ET

from models import PaperMetadata
from retrievers.http_client import get_bytes

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = "http://www.w3.org/2005/Atom"
ARXIV_NS = "http://arxiv.org/schemas/atom"
NS = {"atom": ATOM_NS, "arxiv": ARXIV_NS}
VALID_SORT_BY = {"relevance", "lastUpdatedDate", "submittedDate"}


def search_arxiv(
    query: str,
    max_results: int = 50,
    start: int = 0,
    sort_by: str = "relevance",
) -> list[PaperMetadata]:
    """Search arXiv's public Atom API and return normalized paper metadata."""
    if sort_by not in VALID_SORT_BY:
        valid = ", ".join(sorted(VALID_SORT_BY))
        raise ValueError(f"Invalid sort_by={sort_by!r}. Choose one of: {valid}")

    query = query.strip()
    if not query:
        return []

    params = {
        "search_query": _format_search_query(query),
        "start": max(0, int(start)),
        "max_results": max(1, int(max_results)),
        "sortBy": sort_by,
        "sortOrder": "descending",
    }
    url = f"{ARXIV_API_URL}?{urllib.parse.urlencode(params)}"
    payload = get_bytes(url, rate_limit="arxiv")
    root = ET.fromstring(payload)
    papers = [parse_arxiv_entry(entry) for entry in root.findall("atom:entry", NS)]
    for paper in papers:
        if not paper.sources:
            paper.sources = [paper.source]
    return papers


def parse_arxiv_entry(entry_xml) -> PaperMetadata:
    """Parse one arXiv Atom ``entry`` element into ``PaperMetadata``."""
    entry = _coerce_entry(entry_xml)
    title = _normalize_text(_find_text(entry, "atom:title"))
    abstract = _normalize_text(_find_text(entry, "atom:summary"))
    published = _find_text(entry, "atom:published") or None
    updated = _find_text(entry, "atom:updated") or None
    url = _find_text(entry, "atom:id") or None

    authors = [
        _normalize_text(name.text or "")
        for name in entry.findall("atom:author/atom:name", NS)
        if _normalize_text(name.text or "")
    ]
    categories = _categories(entry)
    pdf_url = _pdf_url(entry)
    paper_id = _paper_id(url)

    return PaperMetadata(
        paper_id=paper_id,
        source="arxiv",
        title=title,
        abstract=abstract,
        authors=authors,
        year=_year_from_date(published),
        published=published,
        updated=updated,
        url=url,
        pdf_url=pdf_url,
        doi=None,
        venue=None,
        citation_count=None,
        fields_of_study=[],
        categories=categories,
        sources=["arxiv"],
    )


def _format_search_query(query: str) -> str:
    if re.search(r"\b(all|ti|au|abs|cat|id|doi|jr):", query):
        return query
    return f"all:{query}"


def _coerce_entry(entry_xml) -> ET.Element:
    if isinstance(entry_xml, ET.Element):
        return entry_xml
    if isinstance(entry_xml, bytes | str):
        return ET.fromstring(entry_xml)
    raise TypeError("entry_xml must be an Element, str, or bytes")


def _find_text(entry: ET.Element, path: str) -> str:
    found = entry.find(path, NS)
    if found is None or found.text is None:
        return ""
    return found.text.strip()


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _categories(entry: ET.Element) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []

    primary = entry.find("arxiv:primary_category", NS)
    if primary is not None:
        term = primary.attrib.get("term", "").strip()
        if term:
            seen.add(term)
            out.append(term)

    for category in entry.findall("atom:category", NS):
        term = category.attrib.get("term", "").strip()
        if term and term not in seen:
            seen.add(term)
            out.append(term)
    return out


def _pdf_url(entry: ET.Element) -> str | None:
    for link in entry.findall("atom:link", NS):
        title = link.attrib.get("title", "").lower()
        link_type = link.attrib.get("type", "").lower()
        href = link.attrib.get("href")
        if href and (title == "pdf" or link_type == "application/pdf"):
            return href
    return None


def _paper_id(url: str | None) -> str:
    if not url:
        return "arxiv:unknown"
    raw_id = url.rstrip("/").split("/")[-1]
    raw_id = re.sub(r"v\d+$", "", raw_id)
    return f"arxiv:{raw_id}"


def _year_from_date(value: str | None) -> int | None:
    if not value or len(value) < 4:
        return None
    try:
        return int(value[:4])
    except ValueError:
        return None
