from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import joblib
import pandas as pd

from cluster import fit_kmeans, top_keywords_per_cluster
from cluster_labels import assign_cluster_labels
from explain import best_matching_sentences, matched_terms, top_weighted_terms_for_doc
from ingest import docs_to_text, load_corpus, load_jsonl_corpus
from rank import rank_by_query, topn_indices
from report import build_report, write_report
from summarize import make_snippet, query_focused_summary
from utils import corpus_fingerprint
from vectorize import build_tfidf

PIPELINE_STEPS = ("rank", "cluster", "summarize", "report")
StatusCallback = Callable[[str], None]


@dataclass
class TriageConfig:
    query: str
    corpus_dir: str | None = None
    jsonl: str | None = None
    topn: int = 10
    n_clusters: int = 4
    top_keywords: int = 10
    summary_sentences: int = 3
    steps: set[str] = field(default_factory=lambda: set(PIPELINE_STEPS))
    cache: bool = False
    out_dir: str = "results"


@dataclass
class PipelineArtifacts:
    out_dir: Path
    ranking_csv: Path
    ranking_json: Path
    clusters_csv: Path
    cluster_keywords_json: Path
    cluster_summaries_json: Path
    summaries_json: Path
    report_md: Path
    corpus_label: str
    n_docs: int
    rank_rows: list[dict]
    cluster_rows: list[dict]
    cluster_keywords: dict[int, list[str]]
    cluster_summaries: dict[int, dict[str, Any]]
    summaries: dict[str, dict]
    steps: set[str]
    cache_path: Path | None = None


PipelineResult = PipelineArtifacts


def ensure_out_dir(out_dir: str) -> Path:
    path = Path(out_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def parse_steps(value: str) -> set[str]:
    if value.strip().lower() == "all":
        return set(PIPELINE_STEPS)
    parts = {part.strip().lower() for part in value.split(",") if part.strip()}
    unknown = parts - set(PIPELINE_STEPS)
    if unknown:
        raise ValueError(
            f"Unknown --steps value(s): {sorted(unknown)}. "
            f"Choose from: {PIPELINE_STEPS} or 'all'."
        )
    return parts


def run_pipeline(
    config: TriageConfig,
    status_callback: StatusCallback | None = None,
) -> PipelineArtifacts:
    """Run the literature triage pipeline for local files or JSONL metadata."""
    _validate_config(config)
    steps = set(config.steps)
    emit = status_callback or (lambda _message: None)

    emit("loading corpus")
    docs, corpus_label = _load_documents(config)

    emit("vectorizing")
    texts = docs_to_text(docs)
    cache_dir = Path(config.out_dir, "cache") if config.cache else None
    vec, X, cache_path = _load_or_build_tfidf(texts, cache_dir)
    outp = ensure_out_dir(config.out_dir)

    emit("ranking")
    scores = rank_by_query(vec, X, config.query)
    idxs = topn_indices(scores, config.topn)

    rank_rows: list[dict] = []
    label_by_doc: dict[str, int] = {}
    labels = None
    cluster_keywords_out: dict[int, list[str]] = {}
    cluster_summaries_out: dict[int, dict[str, Any]] = {}
    cluster_rows: list[dict] = []
    summaries: dict[str, dict] = {}

    if "cluster" in steps or "report" in steps:
        emit("clustering")
        _, labels, distances = fit_kmeans(X, n_clusters=config.n_clusters)
        cluster_keywords_out = top_keywords_per_cluster(
            vec, X, labels, top_k=config.top_keywords
        )
        cluster_labels_out = assign_cluster_labels(cluster_keywords_out)
        label_by_doc = {docs[i].doc_id: int(labels[i]) for i in range(len(docs))}
        cluster_rows = [
            {
                "doc_id": docs[i].doc_id,
                "title": docs[i].title,
                "rel_path": docs[i].rel_path,
                "cluster_id": int(labels[i]),
                "cluster_label": cluster_labels_out[int(labels[i])],
                "distance_to_centroid": float(distances[i]),
            }
            for i in range(len(docs))
        ]
        cluster_summaries_out = _build_cluster_summaries(
            cluster_rows, cluster_keywords_out, cluster_labels_out
        )
        if "cluster" in steps:
            _write_cluster_outputs(
                outp,
                cluster_rows,
                cluster_keywords_out,
                cluster_summaries_out,
            )

    explanation_by_doc: dict[str, dict[str, list[str]]] = {}
    for i in idxs:
        doc = docs[i]
        metadata_fields = _ranking_metadata_fields(getattr(doc, "metadata", None))
        explanation = {
            "matched_query_terms": matched_terms(config.query, texts[i]),
            "top_doc_terms": top_weighted_terms_for_doc(vec, X, i, top_k=10),
            "best_snippets": best_matching_sentences(doc.body, config.query, n=3),
        }
        explanation_by_doc[doc.doc_id] = explanation
        cluster_id = label_by_doc.get(doc.doc_id)
        rank_rows.append(
            {
                "rank": len(rank_rows) + 1,
                "score": float(scores[i]),
                "doc_id": doc.doc_id,
                "title": doc.title,
                "path": doc.path,
                "rel_path": doc.rel_path,
                "word_count": doc.word_count,
                "cluster_id": cluster_id,
                "cluster_label": cluster_summaries_out.get(cluster_id, {}).get("label"),
                **explanation,
                **metadata_fields,
            }
        )

    if "rank" in steps:
        _write_ranking_outputs(outp, rank_rows)

    if "summarize" in steps or "report" in steps:
        emit("summarizing")
        for i in idxs:
            doc = docs[i]
            sentences = query_focused_summary(
                doc.body,
                config.query,
                n_sentences=config.summary_sentences,
            )
            summaries[doc.doc_id] = {
                "title": doc.title,
                "summary": sentences,
                "snippet": make_snippet(doc.body),
                "matched_query_terms": explanation_by_doc.get(doc.doc_id, {}).get(
                    "matched_query_terms", []
                ),
                "best_snippets": explanation_by_doc.get(doc.doc_id, {}).get(
                    "best_snippets", []
                ),
            }
        if "summarize" in steps:
            _write_json(outp / "summaries.json", summaries)

    if "report" in steps:
        report_md = build_report(
            query=config.query,
            corpus_dir=corpus_label,
            n_docs=len(docs),
            rank_rows=rank_rows,
            cluster_rows=cluster_rows,
            cluster_keywords=cluster_keywords_out,
            cluster_summaries=cluster_summaries_out,
            summaries=summaries,
        )
        write_report(outp / "report.md", report_md)

    emit("done")
    artifacts = _artifact_paths(outp)
    return PipelineArtifacts(
        out_dir=outp,
        **artifacts,
        corpus_label=corpus_label,
        n_docs=len(docs),
        rank_rows=rank_rows,
        cluster_rows=cluster_rows,
        cluster_keywords=cluster_keywords_out,
        cluster_summaries=cluster_summaries_out,
        summaries=summaries,
        steps=steps,
        cache_path=cache_path,
    )


def _validate_config(config: TriageConfig) -> None:
    if not config.query.strip():
        raise ValueError("Query cannot be empty.")
    has_corpus_dir = bool(config.corpus_dir)
    has_jsonl = bool(config.jsonl)
    if has_corpus_dir == has_jsonl:
        raise ValueError("Provide exactly one input source: corpus_dir or jsonl.")
    if config.corpus_dir and not Path(config.corpus_dir).is_dir():
        raise FileNotFoundError(f"Corpus directory not found: {config.corpus_dir}")
    if config.jsonl and not Path(config.jsonl).is_file():
        raise FileNotFoundError(f"JSONL file not found: {config.jsonl}")


def _load_documents(config: TriageConfig) -> tuple[list[Any], str]:
    if config.jsonl:
        docs = load_jsonl_corpus(config.jsonl)
        if not docs:
            raise ValueError(f"No paper records found in JSONL file: {config.jsonl}")
        return docs, config.jsonl

    docs = load_corpus(config.corpus_dir or "")
    if not docs:
        raise ValueError(
            f"No usable .txt/.md/.pdf documents found in: {config.corpus_dir}"
        )
    return docs, config.corpus_dir or ""


def _load_or_build_tfidf(
    texts: list[str],
    cache_dir: Path | None,
) -> tuple[Any, Any, Path | None]:
    if cache_dir is None:
        vec, X = build_tfidf(texts)
        return vec, X, None

    fingerprint = corpus_fingerprint(texts)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"tfidf_{fingerprint}.joblib"
    if cache_path.exists():
        try:
            payload = joblib.load(cache_path)
            return payload["vec"], payload["X"], cache_path
        except (OSError, KeyError, ValueError, EOFError) as exc:
            warnings.warn(
                f"Failed to load TF-IDF cache ({cache_path.name}): {exc}; rebuilding.",
                stacklevel=2,
            )

    vec, X = build_tfidf(texts)
    try:
        joblib.dump({"vec": vec, "X": X, "fingerprint": fingerprint}, cache_path)
    except OSError as exc:
        warnings.warn(f"Failed to write TF-IDF cache: {exc}", stacklevel=2)
    return vec, X, cache_path


def _ranking_metadata_fields(metadata: Any) -> dict[str, Any]:
    if metadata is None:
        return {
            "source": None,
            "url": None,
            "pdf_url": None,
            "authors": [],
            "year": None,
            "citation_count": None,
        }
    sources = list(metadata.sources) if metadata.sources else []
    if metadata.source and metadata.source not in sources:
        sources.insert(0, metadata.source)
    return {
        "source": metadata.source,
        "sources": sources,
        "url": metadata.url,
        "pdf_url": metadata.pdf_url,
        "authors": metadata.authors,
        "year": metadata.year,
        "citation_count": metadata.citation_count,
    }


def _build_cluster_summaries(
    cluster_rows: list[dict],
    cluster_keywords: dict[int, list[str]],
    cluster_labels: dict[int, str],
) -> dict[int, dict[str, Any]]:
    summaries: dict[int, dict[str, Any]] = {}
    for cid in sorted(cluster_keywords.keys()):
        members = [row for row in cluster_rows if int(row["cluster_id"]) == cid]
        representatives = sorted(
            members,
            key=lambda row: (float(row["distance_to_centroid"]), row["title"]),
        )[:3]
        summaries[cid] = {
            "cluster_id": cid,
            "label": cluster_labels[cid],
            "keywords": cluster_keywords[cid],
            "number_of_docs": len(members),
            "representative_docs": [
                {
                    "doc_id": row["doc_id"],
                    "title": row["title"],
                    "rel_path": row["rel_path"],
                    "distance_to_centroid": row["distance_to_centroid"],
                }
                for row in representatives
            ],
        }
    return summaries


def _write_cluster_outputs(
    outp: Path,
    cluster_rows: list[dict],
    cluster_keywords: dict[int, list[str]],
    cluster_summaries: dict[int, dict[str, Any]],
) -> None:
    pd.DataFrame(cluster_rows).to_csv(
        outp / "clusters.csv",
        index=False,
        encoding="utf-8",
    )
    _write_json(
        outp / "cluster_keywords.json",
        {str(k): v for k, v in cluster_keywords.items()},
    )
    _write_json(
        outp / "cluster_summaries.json",
        {str(k): v for k, v in cluster_summaries.items()},
    )


def _write_ranking_outputs(outp: Path, rank_rows: list[dict]) -> None:
    pd.DataFrame(rank_rows).to_csv(outp / "ranking.csv", index=False, encoding="utf-8")
    _write_json(outp / "ranking.json", rank_rows)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _artifact_paths(outp: Path) -> dict[str, Path]:
    return {
        "ranking_csv": outp / "ranking.csv",
        "ranking_json": outp / "ranking.json",
        "clusters_csv": outp / "clusters.csv",
        "cluster_keywords_json": outp / "cluster_keywords.json",
        "cluster_summaries_json": outp / "cluster_summaries.json",
        "summaries_json": outp / "summaries.json",
        "report_md": outp / "report.md",
    }
