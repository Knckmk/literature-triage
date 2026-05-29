from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable


def build_report(
    query: str,
    corpus_dir: str,
    n_docs: int,
    rank_rows: list[dict],
    cluster_rows: list[dict],
    cluster_keywords: dict[int, list[str]],
    summaries: dict[str, dict],
    cluster_summaries: dict[int, dict] | None = None,
) -> str:
    """Render a Markdown report from the pipeline outputs."""
    lines: list[str] = []
    lines.append("# Literature Triage Report")
    lines.append("")
    lines.append(f"- **Research question:** {query}")
    lines.append(f"- **Corpus directory:** `{corpus_dir}`")
    lines.append(f"- **Documents indexed:** {n_docs}")
    lines.append(f"- **Top-N reported:** {len(rank_rows)}")
    lines.append("")

    lines.append("## Top-N ranking")
    lines.append("")
    if not rank_rows:
        lines.append("_No documents ranked._")
    else:
        lines.append("| Rank | Score | Cluster | Title | Path |")
        lines.append("|---:|---:|:---:|---|---|")
        for row in rank_rows:
            lines.append(
                "| {rank} | {score:.4f} | {cluster} | {title} | `{path}` |".format(
                    rank=row["rank"],
                    score=float(row["score"]),
                    cluster=_cluster_name(row.get("cluster_id"), row.get("cluster_label")),
                    title=_escape_md(row["title"]),
                    path=row.get("rel_path", row.get("path", "")),
                )
            )
    lines.append("")

    lines.append("## Clusters")
    lines.append("")
    if not cluster_rows:
        lines.append("_No clusters produced._")
    else:
        members_by_cluster: Counter[int] = Counter()
        for row in cluster_rows:
            members_by_cluster[int(row["cluster_id"])] += 1
        for cid in sorted(members_by_cluster.keys()):
            cluster_summary = _cluster_summary(cluster_summaries, cid)
            label = cluster_summary.get("label") or f"Cluster {cid}"
            keywords = (
                cluster_summary.get("keywords")
                or cluster_keywords.get(cid)
                or cluster_keywords.get(str(cid))
                or []
            )
            keyword_text = ", ".join(keywords[:10]) if keywords else "_(no keywords)_"
            lines.append(f"- **Cluster {cid}: {_escape_md(label)}**")
            lines.append(f"  - docs: {members_by_cluster[cid]}")
            lines.append(f"  - keywords: {keyword_text}")
            representative_docs = cluster_summary.get("representative_docs") or []
            if representative_docs:
                titles = ", ".join(
                    _escape_md(doc.get("title", "")) for doc in representative_docs[:3]
                )
                lines.append(f"  - representative docs: {titles}")
    lines.append("")

    lines.append("## Recommended reading order")
    lines.append("")
    if not rank_rows:
        lines.append("_No recommendations available._")
    else:
        for row in rank_rows:
            doc_id = row["doc_id"]
            entry = summaries.get(doc_id, {}) if isinstance(summaries, dict) else {}
            lines.append(f"### {row['rank']}. {_escape_md(row['title'])}")
            lines.append("")
            lines.append(
                f"- score: `{float(row['score']):.4f}` - "
                f"cluster: `{_cluster_name(row.get('cluster_id'), row.get('cluster_label'))}` - "
                f"path: `{row.get('rel_path', row.get('path', ''))}`"
            )

            matched = row.get("matched_query_terms") or entry.get("matched_query_terms")
            if matched:
                lines.append(f"- matched query terms: {', '.join(matched)}")

            best_snippets = row.get("best_snippets") or entry.get("best_snippets")
            if best_snippets:
                lines.append("")
                lines.append("**Why relevant:**")
                for snippet in best_snippets[:3]:
                    lines.append(f"  - {snippet}")

            sentences = entry.get("summary") if isinstance(entry, dict) else None
            if sentences:
                lines.append("")
                lines.append("**Summary:**")
                for sentence in sentences:
                    lines.append(f"  - {sentence}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _escape_md(text: str) -> str:
    """Escape pipe characters so titles do not break Markdown tables."""
    return str(text).replace("|", "\\|")


def _cluster_summary(cluster_summaries: dict[int, dict] | None, cid: int) -> dict:
    if not cluster_summaries:
        return {}
    return cluster_summaries.get(cid) or cluster_summaries.get(str(cid)) or {}


def _cluster_name(cluster_id: object, label: object = None) -> str:
    if cluster_id is None:
        return "-"
    if label:
        return f"Cluster {cluster_id}: {label}"
    return f"Cluster {cluster_id}"


def write_report(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


__all__: Iterable[str] = ("build_report", "write_report")
