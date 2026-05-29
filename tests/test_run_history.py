from __future__ import annotations

import json
from pathlib import Path

from storage import run_history
from storage.run_history import (
    RunMeta,
    RunSummary,
    delete_run,
    register_run,
    rename_run,
    run_display_label,
    write_run_meta,
)


def test_run_display_label_prefers_custom_name():
    run = RunSummary(
        run_id="r1",
        query="original query",
        created_at="2024-01-01T00:00:00Z",
        results_dir="results/runs/r1",
        display_label="My label",
    )
    assert run_display_label(run) == "My label"


def test_rename_and_delete_run(tmp_path, monkeypatch):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True)
    run_history.RESULTS_ROOT = tmp_path
    run_history.RUNS_DIR = runs_dir
    run_history.INDEX_PATH = tmp_path / "index.json"

    run_dir = runs_dir / "test_run"
    run_dir.mkdir()
    meta = RunMeta(
        run_id="test_run",
        query="graph algorithms",
        created_at="2024-01-01T00:00:00Z",
        source_mode="online:arxiv",
        n_docs=5,
        topn=10,
        n_clusters=3,
    )
    write_run_meta(run_dir, meta)
    register_run(meta, run_dir)

    assert rename_run("test_run", "Short name")
    runs = run_history.load_index()
    assert runs[0].display_label == "Short name"
    assert run_display_label(runs[0]) == "Short name"

    meta_payload = json.loads((run_dir / "run_meta.json").read_text(encoding="utf-8"))
    assert meta_payload["display_label"] == "Short name"

    assert delete_run("test_run")
    assert run_history.load_index() == []
    assert not run_dir.exists()
