from __future__ import annotations

import argparse
import time

from retrievers.arxiv_retriever import search_arxiv
from storage.jsonl_store import write_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieve paper metadata from arXiv.")
    parser.add_argument("--query", required=True, help="arXiv search query")
    parser.add_argument("--max_results", type=int, default=50)
    parser.add_argument("--out", required=True, help="Output JSONL path")
    parser.add_argument(
        "--sort_by",
        choices=["relevance", "lastUpdatedDate", "submittedDate"],
        default="relevance",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Optional delay in seconds after retrieval; useful when paging later.",
    )
    args = parser.parse_args()

    papers = search_arxiv(
        query=args.query,
        max_results=args.max_results,
        sort_by=args.sort_by,
    )
    if args.delay > 0:
        time.sleep(args.delay)

    write_jsonl(args.out, papers)
    print(f"Wrote {len(papers)} arXiv records to {args.out}")


if __name__ == "__main__":
    main()
