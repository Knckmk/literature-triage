from __future__ import annotations

import json

from pipeline import PipelineArtifacts, TriageConfig, run_pipeline


def _assert_artifact_paths_exist(artifacts: PipelineArtifacts) -> None:
    assert artifacts.ranking_csv.exists()
    assert artifacts.ranking_json.exists()
    assert artifacts.clusters_csv.exists()
    assert artifacts.cluster_keywords_json.exists()
    assert artifacts.cluster_summaries_json.exists()
    assert artifacts.summaries_json.exists()
    assert artifacts.report_md.exists()


def test_run_pipeline_creates_artifacts_for_local_corpus(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    topics = ["matching", "rounding", "connectivity", "steiner"]
    for idx, topic in enumerate(topics):
        (corpus / f"paper_{idx}.txt").write_text(
            f"Local Paper {idx}\n\n"
            "Graphic TSP approximation uses parity correction, spanning trees, "
            f"matching, and network design ideas with {topic} methods in this "
            "local corpus document.",
            encoding="utf-8",
        )

    artifacts = run_pipeline(
        TriageConfig(
            corpus_dir=str(corpus),
            query="graphic TSP parity correction",
            topn=3,
            n_clusters=2,
            out_dir=str(tmp_path / "local_results"),
        )
    )

    assert isinstance(artifacts, PipelineArtifacts)
    assert artifacts.n_docs == 4
    _assert_artifact_paths_exist(artifacts)


def test_run_pipeline_creates_artifacts_for_jsonl_corpus(tmp_path):
    jsonl_path = tmp_path / "papers.jsonl"
    records = []
    topics = ["matching", "rounding", "connectivity", "steiner", "relaxation"]
    for idx, topic in enumerate(topics):
        records.append(
            {
                "paper_id": f"arxiv:2401.1000{idx}",
                "source": "arxiv",
                "title": f"JSONL Graphic TSP Paper {idx}",
                "abstract": (
                    "This JSONL paper studies graphic TSP approximation, "
                    f"parity correction, matching, and {topic} methods."
                ),
                "authors": [f"Author {idx}"],
                "year": 2024,
                "published": "2024-01-01T00:00:00Z",
                "updated": "2024-01-02T00:00:00Z",
                "url": f"https://arxiv.org/abs/2401.1000{idx}",
                "pdf_url": f"https://arxiv.org/pdf/2401.1000{idx}",
                "doi": None,
                "venue": None,
                "citation_count": idx,
                "fields_of_study": [],
                "categories": ["cs.DS"],
            }
        )
    jsonl_path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )

    artifacts = run_pipeline(
        TriageConfig(
            jsonl=str(jsonl_path),
            query="graphic TSP parity correction",
            topn=3,
            n_clusters=2,
            out_dir=str(tmp_path / "jsonl_results"),
        )
    )

    assert isinstance(artifacts, PipelineArtifacts)
    assert artifacts.n_docs == 5
    _assert_artifact_paths_exist(artifacts)
