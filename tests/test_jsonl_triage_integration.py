from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_triage_pipeline_accepts_jsonl_corpus(tmp_path):
    jsonl_path = tmp_path / "papers.jsonl"
    records = []
    for i in range(5):
        records.append(
            {
                "paper_id": f"arxiv:2401.0000{i}",
                "source": "arxiv",
                "title": f"Graphic TSP Approximation Paper {i}",
                "abstract": (
                    "This paper studies graphic TSP approximation algorithms, "
                    "parity correction, spanning trees, and combinatorial "
                    f"optimization methods for test corpus item {i}."
                ),
                "authors": [f"Author {i}"],
                "year": 2024,
                "published": "2024-01-01T00:00:00Z",
                "updated": "2024-01-02T00:00:00Z",
                "url": f"http://arxiv.org/abs/2401.0000{i}",
                "pdf_url": f"http://arxiv.org/pdf/2401.0000{i}",
                "doi": None,
                "venue": None,
                "citation_count": i,
                "fields_of_study": [],
                "categories": ["cs.DS"],
            }
        )

    with jsonl_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")

    out_dir = tmp_path / "results"
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "triage.py",
            "--jsonl",
            str(jsonl_path),
            "--query",
            "graphic TSP parity correction",
            "--topn",
            "3",
            "--n_clusters",
            "2",
            "--out_dir",
            str(out_dir),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (out_dir / "ranking.json").exists()
    assert (out_dir / "clusters.csv").exists()
    assert (out_dir / "cluster_summaries.json").exists()
    assert (out_dir / "summaries.json").exists()
    assert (out_dir / "report.md").exists()

    ranking = json.loads((out_dir / "ranking.json").read_text(encoding="utf-8"))
    assert ranking[0]["source"] == "arxiv"
    assert ranking[0]["authors"]
    assert ranking[0]["year"] == 2024
    assert ranking[0]["matched_query_terms"]
    assert ranking[0]["top_doc_terms"]
    assert ranking[0]["best_snippets"]

    summaries = json.loads((out_dir / "summaries.json").read_text(encoding="utf-8"))
    first_summary = summaries[ranking[0]["doc_id"]]
    assert first_summary["matched_query_terms"]
    assert first_summary["best_snippets"]

    cluster_summaries = json.loads(
        (out_dir / "cluster_summaries.json").read_text(encoding="utf-8")
    )
    first_cluster = next(iter(cluster_summaries.values()))
    assert first_cluster["label"]
    assert first_cluster["keywords"]
    assert first_cluster["number_of_docs"] > 0
    assert first_cluster["representative_docs"]
