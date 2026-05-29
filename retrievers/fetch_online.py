from __future__ import annotations

import urllib.error
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from retrievers.arxiv_retriever import search_arxiv
from retrievers.merge_corpora import merge_and_dedupe
from retrievers.openalex_retriever import search_openalex
from storage.jsonl_store import write_jsonl

SOURCE_ARXIV = "arxiv"
SOURCE_OPENALEX = "openalex"
VALID_SOURCES = {SOURCE_ARXIV, SOURCE_OPENALEX}
SOURCE_ORDER = [SOURCE_ARXIV, SOURCE_OPENALEX]

StatusCallback = Callable[[str], None] | None


@dataclass
class FetchSummary:
    query: str
    sources_requested: list[str]
    sources_succeeded: list[str] = field(default_factory=list)
    source_errors: dict[str, str] = field(default_factory=dict)
    raw_counts: dict[str, int] = field(default_factory=dict)
    merged_count: int = 0
    jsonl_path: Path | None = None


def fetch_online_corpus(
    query: str,
    *,
    sources: set[str],
    max_results_per_source: int,
    arxiv_sort_by: str = "relevance",
    jsonl_path: Path,
    status_callback: StatusCallback = None,
) -> FetchSummary:
    """Fetch from selected online sources, merge, and write JSONL.

    Individual source failures are recorded but do not abort the run when at
    least one other source returns usable papers.
    """
    query = query.strip()
    if not query:
        raise ValueError("Query cannot be empty.")

    unknown = sources - VALID_SOURCES
    if unknown:
        raise ValueError(f"Unknown sources: {sorted(unknown)}")

    if not sources:
        raise ValueError("Select at least one online source.")

    ordered = [name for name in SOURCE_ORDER if name in sources]
    all_papers: list = []
    raw_counts: dict[str, int] = {}
    sources_succeeded: list[str] = []
    source_errors: dict[str, str] = {}

    for source in ordered:
        _notify(status_callback, _fetch_message(source))
        try:
            papers = _fetch_source(
                source,
                query=query,
                max_results=max_results_per_source,
                arxiv_sort_by=arxiv_sort_by,
            )
        except Exception as exc:  # noqa: BLE001 - continue with other sources
            message = _format_source_error(exc)
            source_errors[source] = message
            raw_counts[source] = 0
            _notify(
                status_callback,
                f"{_source_label(source)}: skipped ({message})",
            )
            continue

        raw_counts[source] = len(papers)
        all_papers.extend(papers)
        sources_succeeded.append(source)
        _notify(
            status_callback,
            f"{_source_label(source)}: {len(papers)} papers",
        )

    merged = merge_and_dedupe(all_papers)
    if not merged:
        failed = ", ".join(
            f"{_source_label(s)} ({source_errors.get(s, 'no results')})"
            for s in ordered
        )
        raise ValueError(
            "No papers could be retrieved from any selected source. "
            f"Details: {failed}. "
            "Try again later, broaden your query, or change source selection."
        )

    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(jsonl_path, merged)

    _notify(
        status_callback,
        f"Merged {len(merged)} unique papers (from {sum(raw_counts.values())} raw)",
    )
    _notify(status_callback, f"Saved corpus to {jsonl_path}")

    if source_errors:
        skipped = ", ".join(
            f"{_source_label(s)} ({source_errors[s]})" for s in ordered if s in source_errors
        )
        _notify(
            status_callback,
            f"Warning: continued without: {skipped}",
        )

    return FetchSummary(
        query=query,
        sources_requested=ordered,
        sources_succeeded=sources_succeeded,
        source_errors=source_errors,
        raw_counts=raw_counts,
        merged_count=len(merged),
        jsonl_path=jsonl_path,
    )


def _fetch_source(
    source: str,
    *,
    query: str,
    max_results: int,
    arxiv_sort_by: str,
):
    if source == SOURCE_ARXIV:
        return search_arxiv(query, max_results=max_results, sort_by=arxiv_sort_by)
    if source == SOURCE_OPENALEX:
        return search_openalex(query, max_results=max_results)
    raise ValueError(f"Unsupported source: {source}")


def _format_source_error(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        if exc.code == 429:
            return "rate limited (HTTP 429)"
        return f"HTTP {exc.code}"
    message = str(exc).strip()
    lowered = message.lower()
    if isinstance(exc, TimeoutError) or "timed out" in lowered:
        return "request timed out"
    if "429" in message:
        return "rate limited"
    if len(message) > 120:
        return message[:117] + "..."
    return message or exc.__class__.__name__


def _fetch_message(source: str) -> str:
    return f"Fetching from {_source_label(source)}..."


def _source_label(source: str) -> str:
    return {
        SOURCE_ARXIV: "arXiv",
        SOURCE_OPENALEX: "OpenAlex",
    }.get(source, source)


def _notify(callback: StatusCallback, message: str) -> None:
    if callback is not None:
        callback(message)


def format_partial_fetch_warning(summary: FetchSummary) -> str:
    """User-facing message when some sources failed but others succeeded."""
    if not summary.source_errors:
        return ""
    failed_lines = [
        f"- **{_source_label(src)}**: {msg}"
        for src, msg in summary.source_errors.items()
    ]
    if summary.sources_succeeded:
        ok = ", ".join(_source_label(s) for s in summary.sources_succeeded)
        intro = f"Analysis continued using data from **{ok}**."
    else:
        intro = "Some sources could not be used."
    return (
        f"{intro}\n\n"
        "The following source(s) were skipped:\n"
        + "\n".join(failed_lines)
    )
