from __future__ import annotations

import argparse
from pathlib import Path

from retrievers.fetch_online import (
    SOURCE_ARXIV,
    SOURCE_OPENALEX,
    VALID_SOURCES,
    fetch_online_corpus,
    format_partial_fetch_warning,
)

SOURCE_ALIASES = {
    "arxiv": SOURCE_ARXIV,
    "openalex": SOURCE_OPENALEX,
}


def _parse_sources(value: str) -> set[str]:
    names = {part.strip().lower() for part in value.split(",") if part.strip()}
    resolved = {SOURCE_ALIASES.get(name, name) for name in names}
    unknown = resolved - VALID_SOURCES
    if unknown:
        valid = ", ".join(sorted(VALID_SOURCES))
        raise ValueError(f"Unknown sources: {sorted(unknown)}. Choose from: {valid}")
    return resolved


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retrieve papers from arXiv and/or OpenAlex."
    )
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument(
        "--sources",
        default="arxiv,openalex",
        help="Comma-separated sources: arxiv, openalex",
    )
    parser.add_argument("--max_results", type=int, default=50, help="Per-source limit")
    parser.add_argument(
        "--sort_by",
        choices=["relevance", "lastUpdatedDate", "submittedDate"],
        default="relevance",
        help="arXiv sort order",
    )
    parser.add_argument(
        "--out",
        default="data/online_corpus.jsonl",
        help="Output JSONL path",
    )
    args = parser.parse_args()

    summary = fetch_online_corpus(
        args.query,
        sources=_parse_sources(args.sources),
        max_results_per_source=args.max_results,
        arxiv_sort_by=args.sort_by,
        jsonl_path=Path(args.out),
        status_callback=print,
    )
    print(
        f"Wrote {summary.merged_count} merged papers to {summary.jsonl_path} "
        f"(raw counts: {summary.raw_counts})"
    )
    warning = format_partial_fetch_warning(summary)
    if warning:
        print(f"WARNING: {warning.replace(chr(10), ' ')}")


if __name__ == "__main__":
    main()
