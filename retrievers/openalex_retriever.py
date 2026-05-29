from __future__ import annotations

import os
import re
import urllib.parse

from models import PaperMetadata
from retrievers.http_client import get_json

OPENALEX_WORKS_URL = "https://api.openalex.org/works"


def search_openalex(
    query: str,
    max_results: int = 50,
    mailto: str | None = None,
) -> list[PaperMetadata]:
    """Search OpenAlex works API and return paper metadata."""
    query = query.strip()
    if not query:
        return []

    mailto = (mailto or os.environ.get("OPENALEX_MAILTO") or "").strip()
    params = {
        "search": query,
        "per-page": max(1, min(int(max_results), 200)),
    }
    if mailto:
        params["mailto"] = mailto

    url = f"{OPENALEX_WORKS_URL}?{urllib.parse.urlencode(params)}"
    payload = get_json(url, rate_limit="openalex")
    results = payload.get("results") or []
    return [parse_openalex_work(item) for item in results if isinstance(item, dict)]


def parse_openalex_work(item: dict) -> PaperMetadata:
    raw_id = str(item.get("id") or "").strip()
    openalex_id = raw_id.rsplit("/", 1)[-1] if raw_id else "unknown"

    doi = item.get("doi")
    if doi:
        doi = str(doi).replace("https://doi.org/", "").strip()

    title = _openalex_title(item.get("title"))
    abstract = reconstruct_abstract(item.get("abstract_inverted_index"))

    authors = []
    for authorship in item.get("authorships") or []:
        if not isinstance(authorship, dict):
            continue
        author = authorship.get("author") or {}
        if isinstance(author, dict) and author.get("display_name"):
            authors.append(str(author["display_name"]).strip())

    year = item.get("publication_year")
    try:
        year = int(year) if year is not None else None
    except (TypeError, ValueError):
        year = None

    cited_by = item.get("cited_by_count")
    try:
        citation_count = int(cited_by) if cited_by is not None else None
    except (TypeError, ValueError):
        citation_count = None

    concepts = item.get("concepts") or []
    fields = []
    for concept in concepts:
        if isinstance(concept, dict) and concept.get("display_name"):
            fields.append(str(concept["display_name"]))

    primary_location = item.get("primary_location") or {}
    venue = None
    if isinstance(primary_location, dict):
        source = primary_location.get("source") or {}
        if isinstance(source, dict):
            venue = source.get("display_name")

    pdf_url = resolve_openalex_pdf_url(item)
    record_url = _resolve_openalex_record_url(item, doi=doi)

    published = item.get("publication_date")

    return PaperMetadata(
        paper_id=f"openalex:{openalex_id}",
        source="openalex",
        title=title,
        abstract=abstract,
        authors=authors,
        year=year,
        published=str(published) if published else None,
        updated=None,
        url=record_url,
        pdf_url=pdf_url,
        doi=doi,
        venue=str(venue).strip() if venue else None,
        citation_count=citation_count,
        fields_of_study=fields,
        categories=[],
        sources=["openalex"],
    )


def resolve_openalex_pdf_url(item: dict) -> str | None:
    """Return the best available full-text link for an OpenAlex work."""
    candidates: list[str] = []

    for key in ("primary_location", "best_oa_location"):
        pdf = _location_pdf_url(item.get(key))
        if pdf:
            candidates.append(pdf)

    for loc in item.get("locations") or []:
        pdf = _location_pdf_url(loc)
        if pdf and pdf not in candidates:
            candidates.append(pdf)

    open_access = item.get("open_access")
    if isinstance(open_access, dict) and open_access.get("is_oa"):
        oa_url = open_access.get("oa_url")
        if oa_url:
            url = str(oa_url).strip()
            if url and url not in candidates:
                candidates.append(url)

    for url in candidates:
        if _is_probable_pdf_url(url):
            return url

    return candidates[0] if candidates else None


def _resolve_openalex_record_url(item: dict, *, doi: str | None) -> str | None:
    """Landing page for the work (publisher, repository, or OpenAlex)."""
    for key in ("primary_location", "best_oa_location"):
        location = item.get(key)
        if not isinstance(location, dict):
            continue
        landing = location.get("landing_page_url")
        if landing:
            return str(landing).strip()

    for loc in item.get("locations") or []:
        if not isinstance(loc, dict):
            continue
        landing = loc.get("landing_page_url")
        if landing:
            return str(landing).strip()

    raw_id = item.get("id")
    if raw_id:
        return str(raw_id).strip()
    if doi:
        return f"https://doi.org/{doi}"
    return None


def _location_pdf_url(location: object) -> str | None:
    if not isinstance(location, dict):
        return None
    pdf = location.get("pdf_url")
    if pdf:
        return str(pdf).strip()
    return None


def _is_probable_pdf_url(url: str) -> bool:
    path = url.lower().split("?", 1)[0]
    if path.endswith(".pdf"):
        return True
    if "/pdf/" in path or "arxiv.org/pdf/" in path:
        return True
    return False


def reconstruct_abstract(inverted_index: object) -> str:
    """Rebuild plain-text abstract from OpenAlex abstract_inverted_index."""
    if not isinstance(inverted_index, dict) or not inverted_index:
        return ""

    positions: list[tuple[int, str]] = []
    for word, idxs in inverted_index.items():
        if not isinstance(idxs, list):
            continue
        for idx in idxs:
            try:
                positions.append((int(idx), str(word)))
            except (TypeError, ValueError):
                continue

    if not positions:
        return ""

    positions.sort(key=lambda pair: pair[0])
    return " ".join(word for _, word in positions).strip()


def _openalex_title(value: object) -> str:
    if not value:
        return ""
    text = str(value).strip()
    return re.sub(r"\s+", " ", text)
