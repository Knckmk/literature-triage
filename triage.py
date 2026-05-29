from __future__ import annotations

import argparse

from pipeline import TriageConfig, parse_steps, run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Literature Triage pipeline: ingest -> TF-IDF -> rank "
            "-> cluster -> summarize -> report"
        )
    )
    parser.add_argument("--corpus_dir", help="Folder containing .txt/.md/.pdf docs")
    parser.add_argument("--jsonl", help="JSONL paper metadata corpus path")
    parser.add_argument("--query", required=True, help="Research question / query string")
    parser.add_argument("--topn", type=int, default=10, help="How many top docs to output")
    parser.add_argument(
        "--n_clusters",
        type=int,
        default=4,
        help="KMeans cluster count (auto-clamped if > n_docs)",
    )
    parser.add_argument(
        "--top_keywords",
        type=int,
        default=10,
        help="How many keywords to extract per cluster",
    )
    parser.add_argument(
        "--summary_sentences",
        type=int,
        default=3,
        help="How many sentences to keep in the query-focused summary",
    )
    parser.add_argument(
        "--steps",
        default="all",
        help=(
            "Comma-separated pipeline steps to run. "
            "Choices: rank, cluster, summarize, report (or 'all')."
        ),
    )
    parser.add_argument(
        "--cache",
        action="store_true",
        help="Cache TF-IDF artifacts in <out_dir>/cache for faster re-runs.",
    )
    parser.add_argument("--out_dir", default="results", help="Output directory")
    args = parser.parse_args()

    try:
        steps = parse_steps(args.steps)
        result = run_pipeline(
            TriageConfig(
                corpus_dir=args.corpus_dir,
                jsonl=args.jsonl,
                query=args.query,
                topn=args.topn,
                n_clusters=args.n_clusters,
                top_keywords=args.top_keywords,
                summary_sentences=args.summary_sentences,
                steps=steps,
                cache=args.cache,
                out_dir=args.out_dir,
            )
        )
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    print(f"Pipeline finished - steps: {sorted(result.steps)}")
    print(f"Indexed documents: {result.n_docs}")
    if result.cache_path is not None:
        print(f"TF-IDF cache: {result.cache_path}")
    print(f"Output directory: {result.out_dir}")
    print("\nTop results:")
    for row in result.rank_rows:
        cluster = row.get("cluster_label") or row.get("cluster_id")
        cluster_str = "-" if cluster is None else str(cluster)
        print(f"{row['rank']:>2}. {row['score']:.4f} | {cluster_str} | {row['title']}")

    if result.cluster_summaries:
        print("\nClusters:")
        for cid in sorted(result.cluster_summaries.keys()):
            summary = result.cluster_summaries[cid]
            keywords = ", ".join(summary["keywords"][:8]) or "(no terms)"
            print(
                f"  cluster {cid} - {summary['label']} "
                f"({summary['number_of_docs']} docs): {keywords}"
            )


if __name__ == "__main__":
    main()
