from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils import slugify

RESULTS_ROOT = Path("results")
RUNS_DIR = RESULTS_ROOT / "runs"
INDEX_PATH = RESULTS_ROOT / "index.json"
LEGACY_RUN_ID = "legacy"  # filtered out of sidebar history
MAX_RUNS = 20


@dataclass
class RunSummary:
    run_id: str
    query: str
    created_at: str
    results_dir: str
    n_docs: int = 0
    source_mode: str = ""
    display_label: str = ""


@dataclass
class RunMeta:
    run_id: str
    query: str
    created_at: str
    source_mode: str
    n_docs: int
    topn: int
    n_clusters: int
    summary_sentences: int = 3
    retrieval_sources: list[str] = field(default_factory=list)
    display_label: str = ""


def _ensure_results_root() -> None:
    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


def _is_legacy_entry(item: dict[str, Any]) -> bool:
    run_id = str(item.get("run_id", ""))
    return run_id == LEGACY_RUN_ID or str(item.get("source_mode", "")) == "legacy"


def _purge_legacy_entries(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in runs if not _is_legacy_entry(item)]


def load_index() -> list[RunSummary]:
    _ensure_results_root()
    if not INDEX_PATH.exists():
        return []
    try:
        payload = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    runs = payload.get("runs", [])
    if not isinstance(runs, list):
        return []
    cleaned = _purge_legacy_entries(runs)
    if len(cleaned) != len(runs):
        INDEX_PATH.write_text(
            json.dumps({"runs": cleaned}, indent=2),
            encoding="utf-8",
        )
        runs = cleaned
    out: list[RunSummary] = []
    for item in runs:
        if not isinstance(item, dict) or not item.get("run_id"):
            continue
        out.append(
            RunSummary(
                run_id=str(item["run_id"]),
                query=str(item.get("query", "")),
                created_at=str(item.get("created_at", "")),
                results_dir=str(item.get("results_dir", "")),
                n_docs=int(item.get("n_docs", 0)),
                source_mode=str(item.get("source_mode", "")),
                display_label=str(item.get("display_label", "")),
            )
        )
    return out


def save_index(runs: list[RunSummary]) -> None:
    _ensure_results_root()
    payload = {"runs": [asdict(run) for run in runs]}
    INDEX_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def make_run_id(query: str) -> str:
    slug = slugify(query.strip()[:80], max_len=40)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base = f"{slug}_{ts}" if slug else f"run_{ts}"
    candidate = base
    suffix = 2
    while (RUNS_DIR / candidate).exists():
        candidate = f"{base}_{suffix}"
        suffix += 1
    return candidate


def allocate_run_dir(query: str) -> tuple[str, Path]:
    _ensure_results_root()
    run_id = make_run_id(query)
    path = RUNS_DIR / run_id
    path.mkdir(parents=True, exist_ok=False)
    return run_id, path


def resolve_results_dir(run_id: str) -> Path | None:
    for run in load_index():
        if run.run_id == run_id:
            return Path(run.results_dir)
    return None


def get_run(run_id: str) -> RunSummary | None:
    for run in load_index():
        if run.run_id == run_id:
            return run
    return None


def run_display_label(run: RunSummary) -> str:
    """Sidebar / header label: custom name if set, otherwise the search query."""
    custom = (run.display_label or "").strip()
    return custom if custom else run.query.strip()


def rename_run(run_id: str, new_label: str) -> bool:
    """Set the visible label for a saved run. Returns False if run_id is unknown."""
    runs = load_index()
    updated = False
    for run in runs:
        if run.run_id != run_id:
            continue
        run.display_label = new_label.strip()
        _sync_run_meta_display_label(Path(run.results_dir), run.display_label)
        updated = True
        break
    if updated:
        save_index(runs)
    return updated


def delete_run(run_id: str) -> bool:
    """Remove a run from the index and delete its results directory."""
    runs = load_index()
    target: RunSummary | None = None
    kept: list[RunSummary] = []
    for run in runs:
        if run.run_id == run_id:
            target = run
        else:
            kept.append(run)
    if target is None:
        return False
    save_index(kept)
    path = Path(target.results_dir)
    if path.is_dir() and path.resolve().parent == RUNS_DIR.resolve():
        shutil.rmtree(path, ignore_errors=True)
    return True


def _sync_run_meta_display_label(results_dir: Path, display_label: str) -> None:
    meta_path = results_dir / "run_meta.json"
    if not meta_path.exists():
        return
    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    if not isinstance(payload, dict):
        return
    payload["display_label"] = display_label
    meta_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_run_meta(results_dir: Path, meta: RunMeta) -> None:
    path = results_dir / "run_meta.json"
    path.write_text(json.dumps(asdict(meta), indent=2), encoding="utf-8")


def register_run(meta: RunMeta, results_dir: Path) -> None:
    runs = load_index()
    runs = [r for r in runs if r.run_id != meta.run_id]
    summary = RunSummary(
        run_id=meta.run_id,
        query=meta.query,
        created_at=meta.created_at,
        results_dir=str(results_dir),
        n_docs=meta.n_docs,
        source_mode=meta.source_mode,
        display_label=meta.display_label,
    )
    runs.insert(0, summary)
    _trim_runs(runs)


def _trim_runs(runs: list[RunSummary]) -> None:
    if len(runs) <= MAX_RUNS:
        save_index(runs)
        return
    kept = runs[:MAX_RUNS]
    removed = runs[MAX_RUNS:]
    save_index(kept)
    for run in removed:
        path = Path(run.results_dir)
        if path.is_dir() and path.resolve().parent == RUNS_DIR.resolve():
            shutil.rmtree(path, ignore_errors=True)


def list_runs() -> list[RunSummary]:
    return load_index()
