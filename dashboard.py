"""
Streamlit dashboard for the Literature Triage Tool.

Single-page layout with search history in the sidebar and per-run result storage.
"""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import streamlit as st

from pipeline import TriageConfig, run_pipeline
from retrievers.fetch_online import (
    SOURCE_ARXIV,
    SOURCE_OPENALEX,
    fetch_online_corpus,
    format_partial_fetch_warning,
)
from storage.run_history import (
    RunMeta,
    RunSummary,
    allocate_run_dir,
    list_runs,
    load_index,
    register_run,
    resolve_results_dir,
    run_display_label,
    write_run_meta,
)

DEFAULT_ONLINE_JSONL = Path("data/online_corpus.jsonl")
DEFAULT_ARXIV_JSONL = Path("data/arxiv_corpus.jsonl")
DEFAULT_CORPUS_DIR = Path("examples/corpus")

INPUT_MODE_ONLINE = "online"
INPUT_MODE_JSONL = "jsonl"
INPUT_MODE_LOCAL = "local"


def _init_session_state() -> None:
    defaults = {
        "selected_run_id": None,
        "show_new_analysis": True,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _load_json(path: Path) -> object | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _load_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        return None


def _results_summary(results_dir: Path) -> dict[str, Any]:
    return {
        "ranking": _load_json(results_dir / "ranking.json"),
        "clusters": _load_csv(results_dir / "clusters.csv"),
        "cluster_keywords": _load_json(results_dir / "cluster_keywords.json"),
        "cluster_summaries": _load_json(results_dir / "cluster_summaries.json"),
        "summaries": _load_json(results_dir / "summaries.json"),
    }


def _format_score(score: object) -> str:
    return f"{float(score):.4f}" if isinstance(score, (int, float)) else "-"


def _has_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, float) and pd.isna(value):
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    return True


def _format_sources(value: object) -> str:
    if isinstance(value, list):
        labels = []
        for item in value:
            text = str(item).strip()
            if not text:
                continue
            labels.append(
                {
                    "arxiv": "arXiv",
                    "openalex": "OpenAlex",
                }.get(text, text)
            )
        if labels:
            return " · ".join(labels)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return ""


def _format_authors(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(v) for v in value if str(v).strip())
    if isinstance(value, str):
        return value
    return ""


def _cluster_label(cluster_summaries: dict, cluster_id: int) -> str:
    summary = cluster_summaries.get(str(cluster_id)) or cluster_summaries.get(cluster_id)
    if isinstance(summary, dict) and summary.get("label"):
        return str(summary["label"])
    return f"Cluster {cluster_id}"


def _chip_html(values: list[str]) -> str:
    chips = []
    for value in values:
        escaped = html.escape(str(value))
        chips.append(
            "<span style='display:inline-block;padding:0.15rem 0.45rem;"
            "margin:0 0.25rem 0.25rem 0;border-radius:999px;"
            "background:#eef2ff;color:#1e3a8a;font-size:0.85rem;'>"
            f"{escaped}</span>"
        )
    return "".join(chips)


def _format_run_date(created_at: str) -> str:
    if not created_at:
        return ""
    try:
        normalized = created_at.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        return dt.strftime("%b %d, %Y")
    except ValueError:
        return created_at[:10]


def _format_run_datetime(created_at: str) -> str:
    if not created_at:
        return ""
    try:
        normalized = created_at.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        return dt.strftime("%b %d, %Y · %H:%M UTC")
    except ValueError:
        return created_at[:16]


def _inject_sidebar_history_styles() -> None:
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] .sidebar-history-label {
            font-size: 0.78rem;
            font-weight: 600;
            color: rgba(128, 128, 128, 0.95);
            margin: 0.75rem 0 0.35rem 0.55rem;
            letter-spacing: 0.02em;
        }
        section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"]
            div.stButton:not(:first-of-type) > button[kind="secondary"],
        section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"]
            div.stButton:not(:first-of-type) > button[kind="primary"] {
            background: transparent !important;
            border: 1px solid rgba(128, 128, 128, 0.35) !important;
            box-shadow: none !important;
            color: inherit !important;
            text-align: left !important;
            justify-content: flex-start !important;
            width: 100% !important;
            min-height: 2rem !important;
            padding: 0.35rem 0.55rem !important;
            margin: 0 0 0.2rem 0 !important;
            font-size: 0.82rem !important;
            font-weight: 400 !important;
            line-height: 1.25 !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            border-radius: 0.5rem !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"]
            div.stButton:not(:first-of-type) > button[kind="secondary"]:hover,
        section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"]
            div.stButton:not(:first-of-type) > button[kind="primary"]:hover {
            background: rgba(128, 128, 128, 0.14) !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"]
            div.stButton:not(:first-of-type) > button[kind="primary"] {
            background: rgba(128, 128, 128, 0.28) !important;
            border-color: rgba(255, 255, 255, 0.22) !important;
            font-weight: 500 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"]
            div.stButton:not(:first-of-type) > button p {
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            white-space: nowrap !important;
            margin: 0 !important;
            text-align: left !important;
        }
        .results-header {
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            gap: 1rem;
            margin: 0 0 1rem 0;
        }
        .results-header-query {
            font-size: 1.05rem;
            font-weight: 600;
            line-height: 1.35;
            flex: 1;
            min-width: 0;
        }
        .results-header-date {
            font-size: 0.82rem;
            color: rgba(128, 128, 128, 0.95);
            white-space: nowrap;
            text-align: right;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _download_outputs(results_dir: Path, run_id: str) -> None:
    st.subheader("Downloads")
    cols = st.columns(3)
    downloads = [
        ("ranking.csv", "Download ranking.csv", "text/csv"),
        ("report.md", "Download report.md", "text/markdown"),
        ("summaries.json", "Download summaries.json", "application/json"),
    ]
    for col, (filename, label, mime) in zip(cols, downloads):
        path = results_dir / filename
        disabled = not path.exists()
        data = path.read_bytes() if path.exists() else b""
        col.download_button(
            label,
            data=data,
            file_name=filename,
            mime=mime,
            disabled=disabled,
            use_container_width=True,
            key=f"download_{run_id}_{filename}",
        )


def _prepare_ranking_df(data: dict[str, Any]) -> pd.DataFrame:
    ranking = data["ranking"] or []
    ranking_df = pd.DataFrame(ranking)
    clusters_df = data["clusters"]
    cluster_summaries = data["cluster_summaries"] or {}

    if ranking_df.empty:
        return ranking_df
    if clusters_df is not None and "cluster_id" not in ranking_df.columns:
        ranking_df = ranking_df.merge(
            clusters_df[["doc_id", "cluster_id"]],
            on="doc_id",
            how="left",
        )
    if "cluster_id" in ranking_df.columns:
        ranking_df["cluster_label"] = ranking_df["cluster_id"].map(
            lambda cid: _cluster_label(cluster_summaries, int(cid))
            if pd.notna(cid)
            else None
        )
    return ranking_df


def _render_cluster_panel(cluster_keywords: dict, cluster_summaries: dict) -> None:
    st.subheader("Clusters")
    if cluster_summaries:
        for cid in sorted(cluster_summaries.keys(), key=lambda x: int(x)):
            summary = cluster_summaries[cid]
            label = summary.get("label", f"Cluster {cid}")
            keywords = summary.get("keywords", [])
            n_docs = summary.get("number_of_docs", 0)
            st.markdown(f"**Cluster {cid} - {label}**")
            st.caption(f"{n_docs} documents")
            if keywords:
                st.write(", ".join(keywords[:10]))
            reps = summary.get("representative_docs", [])
            if reps:
                st.caption("Representative docs")
                for doc in reps[:3]:
                    st.markdown(f"- {doc.get('title', '')}")
        return

    if not cluster_keywords:
        st.caption("No cluster keywords found.")
        return

    for cid in sorted(cluster_keywords.keys(), key=lambda x: int(x)):
        keywords = cluster_keywords[cid]
        if keywords:
            st.markdown(f"**Cluster {cid}** - " + ", ".join(keywords[:10]))


def _render_paper_card(row: pd.Series) -> None:
    with st.container(border=True):
        st.markdown(f"#### {row.get('rank', '-')}. {row.get('title', '')}")
        meta = [f"score `{_format_score(row.get('score'))}`"]
        source_label = _format_sources(row.get("sources")) or (
            str(row.get("source")) if _has_value(row.get("source")) else ""
        )
        if source_label:
            meta.append(source_label)
        if _has_value(row.get("year")):
            meta.append(str(int(row.get("year"))))
        if _has_value(row.get("cluster_label")):
            meta.append(str(row.get("cluster_label")))
        st.caption(" - ".join(meta))

        authors = _format_authors(row.get("authors"))
        if authors:
            st.write(authors)

        matched = row.get("matched_query_terms", [])
        if _has_value(matched):
            values = matched if isinstance(matched, list) else [str(matched)]
            st.markdown(_chip_html(values), unsafe_allow_html=True)

        link_parts: list[str] = []
        if _has_value(row.get("url")):
            url = html.escape(str(row.get("url")))
            link_parts.append(f"[Open record]({url})")
        if _has_value(row.get("pdf_url")):
            pdf_url = html.escape(str(row.get("pdf_url")))
            link_parts.append(f"[Open PDF]({pdf_url})")
        if link_parts:
            st.markdown(" · ".join(link_parts))


def _render_document_detail(
    ranking_df: pd.DataFrame,
    summaries: dict,
    cluster_keywords: dict,
    cluster_summaries: dict,
    selected_doc_id: str | None,
) -> None:
    st.subheader("Document detail")
    if ranking_df.empty or not selected_doc_id:
        st.caption("Select a document from the list.")
        return

    row = ranking_df.set_index("doc_id").loc[selected_doc_id]
    st.markdown(f"### {row['title']}")
    meta = [f"score `{_format_score(row.get('score'))}`"]
    if _has_value(row.get("cluster_label")):
        meta.append(str(row.get("cluster_label")))
    if _has_value(row.get("rel_path")):
        meta.append(f"path `{row.get('rel_path')}`")
    st.caption(" - ".join(meta))

    metadata_rows = []
    for label, key in [
        ("Source", "source"),
        ("Authors", "authors"),
        ("Year", "year"),
        ("URL", "url"),
        ("PDF", "pdf_url"),
        ("Citations", "citation_count"),
    ]:
        value = row.get(key)
        if not _has_value(value):
            continue
        if key == "authors":
            value = _format_authors(value)
        metadata_rows.append((label, value))

    if metadata_rows:
        st.markdown("**Metadata**")
        for label, value in metadata_rows:
            if label in {"URL", "PDF"}:
                st.markdown(f"- **{label}:** [{value}]({value})")
            else:
                st.markdown(f"- **{label}:** {value}")

    summary_entry = summaries.get(selected_doc_id, {})
    matched = row.get("matched_query_terms", [])
    best_snippets = row.get("best_snippets", [])
    if not _has_value(matched) and isinstance(summary_entry, dict):
        matched = summary_entry.get("matched_query_terms", [])
    if not _has_value(best_snippets) and isinstance(summary_entry, dict):
        best_snippets = summary_entry.get("best_snippets", [])

    if _has_value(matched) or _has_value(best_snippets):
        st.markdown("**Why this paper?**")
        if _has_value(matched):
            matched_values = matched if isinstance(matched, list) else [str(matched)]
            st.markdown(_chip_html(matched_values), unsafe_allow_html=True)
        if _has_value(best_snippets):
            for snippet in best_snippets[:3]:
                st.markdown(f"- {snippet}")

    sentences = summary_entry.get("summary", []) if isinstance(summary_entry, dict) else []
    snippet = summary_entry.get("snippet", "") if isinstance(summary_entry, dict) else ""
    st.markdown("**Query-focused summary**")
    if sentences:
        for sentence in sentences:
            st.markdown(f"- {sentence}")
    else:
        st.caption("No summary generated for this document.")

    if snippet:
        st.markdown("**Snippet**")
        st.write(snippet)

    if _has_value(row.get("cluster_id")):
        cid = str(int(row.get("cluster_id")))
        cluster_summary = cluster_summaries.get(cid, {})
        keywords = cluster_summary.get("keywords") or cluster_keywords.get(cid, [])
        if keywords:
            label = cluster_summary.get("label", f"Cluster {cid}")
            st.markdown(f"**Cluster keywords: {label}**")
            st.write(", ".join(keywords[:15]))


def _render_results_header(query_label: str | None, searched_at: str | None) -> None:
    if not query_label and not searched_at:
        return
    query_html = html.escape(query_label or "")
    date_html = html.escape(_format_run_datetime(searched_at or ""))
    st.markdown(
        f"""
        <div class="results-header">
            <div class="results-header-query">{query_html}</div>
            <div class="results-header-date">{date_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_results(
    results_dir: Path,
    run_id: str,
    query_label: str | None = None,
    searched_at: str | None = None,
) -> None:
    data = _results_summary(results_dir)
    ranking_df = _prepare_ranking_df(data)
    cluster_keywords = data["cluster_keywords"] or {}
    cluster_summaries = data["cluster_summaries"] or {}
    summaries = data["summaries"] or {}

    if ranking_df.empty:
        st.warning(
            f"`{results_dir}` does not contain `ranking.json`. "
            "Run a new analysis from the sidebar."
        )
        return

    _render_results_header(query_label, searched_at)

    _download_outputs(results_dir, run_id)

    available_clusters = sorted(
        {int(v) for v in ranking_df["cluster_id"].dropna()}
        if "cluster_id" in ranking_df.columns
        else set()
    )
    controls = st.columns([2, 1])
    cluster_choice = controls[0].selectbox(
        "Cluster filter",
        options=[None] + available_clusters,
        format_func=lambda c: "All clusters"
        if c is None
        else f"Cluster {c} - {_cluster_label(cluster_summaries, c)}",
        key=f"cluster_filter_{run_id}",
    )
    topn_limit = controls[1].slider(
        "Show top-N",
        min_value=1,
        max_value=max(1, len(ranking_df)),
        value=min(10, len(ranking_df)),
        key=f"topn_{run_id}",
    )

    filtered = ranking_df.copy()
    if cluster_choice is not None:
        filtered = filtered[filtered["cluster_id"] == cluster_choice]
    filtered = filtered.head(topn_limit)

    left, right = st.columns([3, 4], gap="large")
    with left:
        st.subheader("Ranked papers")
        display_cols = [
            col
            for col in [
                "rank",
                "score",
                "title",
                "source",
                "year",
                "cluster_label",
                "word_count",
                "citation_count",
            ]
            if col in filtered.columns
        ]
        view = filtered[display_cols].copy()
        if "score" in view.columns:
            view["score"] = view["score"].map(_format_score)
        st.dataframe(view, hide_index=True, use_container_width=True)

        doc_options = filtered["doc_id"].tolist()
        selected_doc_id = None
        if doc_options:
            selected_doc_id = st.selectbox(
                "Inspect document",
                options=doc_options,
                format_func=lambda doc_id: (
                    f"{doc_id} | "
                    f"{ranking_df.set_index('doc_id').loc[doc_id, 'title']}"
                ),
                key=f"inspect_doc_{run_id}",
            )

        st.subheader("Paper cards")
        for _, row in filtered.iterrows():
            _render_paper_card(row)

        _render_cluster_panel(cluster_keywords, cluster_summaries)

    with right:
        _render_document_detail(
            ranking_df,
            summaries,
            cluster_keywords,
            cluster_summaries,
            selected_doc_id,
        )


def _resolve_jsonl_path() -> Path:
    if DEFAULT_ONLINE_JSONL.exists():
        return DEFAULT_ONLINE_JSONL
    return DEFAULT_ARXIV_JSONL


def _render_sidebar_history() -> None:
    _inject_sidebar_history_styles()

    if st.sidebar.button("New analysis", use_container_width=True, type="primary"):
        st.session_state.show_new_analysis = True
        st.session_state.selected_run_id = None
        st.rerun()

    runs = list_runs()
    if not runs:
        st.sidebar.caption("No saved analyses yet. Run your first search below.")
        return

    st.sidebar.markdown(
        '<p class="sidebar-history-label">Search history</p>',
        unsafe_allow_html=True,
    )
    for run in runs:
        _render_sidebar_history_row(run)


def _render_sidebar_history_row(run: RunSummary) -> None:
    label = run_display_label(run)
    is_selected = (
        not st.session_state.show_new_analysis
        and st.session_state.selected_run_id == run.run_id
    )
    help_text = run.query.strip()
    if run.display_label.strip() and run.display_label.strip() != help_text:
        help_text = f"{label}\n\nQuery: {help_text}"

    if st.sidebar.button(
        label,
        key=f"history_{run.run_id}",
        use_container_width=True,
        type="primary" if is_selected else "secondary",
        help=help_text,
    ):
        st.session_state.selected_run_id = run.run_id
        st.session_state.show_new_analysis = False
        st.rerun()


def _render_new_analysis_form() -> None:
    st.subheader("New analysis")
    st.caption("Fetch papers from selected online sources and rank them for your research question.")

    input_mode = INPUT_MODE_ONLINE
    corpus_dir: str | None = None
    jsonl_path: str | None = None
    fetch_online = True
    retrieval_sources: set[str] = set()
    max_per_source = 50
    arxiv_sort_by = "relevance"

    with st.expander("Advanced options", expanded=False):
        mode_labels = {
            INPUT_MODE_ONLINE: "Online sources",
            INPUT_MODE_JSONL: "JSONL file",
            INPUT_MODE_LOCAL: "Local corpus folder",
        }
        input_mode = st.radio(
            "Input mode",
            options=list(mode_labels.keys()),
            format_func=lambda k: mode_labels[k],
            horizontal=True,
            index=0,
        )

        if input_mode == INPUT_MODE_ONLINE:
            st.markdown("**Online sources**")
            use_arxiv = st.checkbox("arXiv", value=True)
            use_openalex = st.checkbox("OpenAlex", value=True)
            max_per_source = st.number_input(
                "Maximum papers per source",
                min_value=10,
                max_value=200,
                value=50,
                help="Each selected source fetches up to this many papers.",
            )
            if use_arxiv:
                arxiv_sort_by = st.selectbox(
                    "arXiv sort by",
                    options=["relevance", "lastUpdatedDate", "submittedDate"],
                    format_func=lambda v: {
                        "relevance": "Relevance",
                        "lastUpdatedDate": "Last updated",
                        "submittedDate": "Submitted date",
                    }[v],
                )
            fetch_online = True
            jsonl_path = str(DEFAULT_ONLINE_JSONL)
            if use_arxiv:
                retrieval_sources.add(SOURCE_ARXIV)
            if use_openalex:
                retrieval_sources.add(SOURCE_OPENALEX)
        elif input_mode == INPUT_MODE_JSONL:
            fetch_online = False
            jsonl_path = st.text_input(
                "JSONL file path",
                value=str(_resolve_jsonl_path()),
            )
        else:
            fetch_online = False
            corpus_dir = st.text_input(
                "Corpus directory",
                value=str(DEFAULT_CORPUS_DIR),
            )

    query = st.text_area(
        "Research question / search query",
        value="",
        height=90,
        placeholder="e.g. 2-edge-connected spanning subgraph approximation",
    )
    cols = st.columns(3)
    topn = cols[0].number_input("Top-N results", min_value=1, max_value=100, value=10)
    n_clusters = cols[1].number_input("Number of clusters", min_value=1, max_value=50, value=4)
    summary_sentences = cols[2].number_input(
        "Summary sentences",
        min_value=1,
        max_value=10,
        value=3,
    )

    run_clicked = st.button("Run analysis", type="primary")
    if not run_clicked:
        return

    if not query.strip():
        st.error("Please enter a research question or search query.")
        return

    if fetch_online and not retrieval_sources:
        st.error("Select at least one online source in Advanced options.")
        return

    run_id, run_dir = allocate_run_dir(query.strip())
    status_lines: list[str] = []
    status_box = st.empty()

    def update_status(message: str) -> None:
        status_lines.append(message)
        status_box.info(" → ".join(status_lines))

    fetch_summary = None
    try:
        if fetch_online:
            fetch_summary = fetch_online_corpus(
                query.strip(),
                sources=retrieval_sources,
                max_results_per_source=int(max_per_source),
                arxiv_sort_by=arxiv_sort_by,
                jsonl_path=Path(jsonl_path or DEFAULT_ONLINE_JSONL),
                status_callback=update_status,
            )
            retrieval_sources = set(fetch_summary.sources_succeeded)
            if fetch_summary.source_errors:
                warning_text = format_partial_fetch_warning(fetch_summary)
                st.session_state.partial_fetch_warning = warning_text
                st.warning(warning_text, icon="⚠️")

        config = TriageConfig(
            corpus_dir=corpus_dir,
            jsonl=jsonl_path,
            query=query.strip(),
            topn=int(topn),
            n_clusters=int(n_clusters),
            summary_sentences=int(summary_sentences),
            out_dir=str(run_dir),
            cache=True,
        )
        result = run_pipeline(config, status_callback=update_status)
    except (FileNotFoundError, ValueError) as exc:
        st.error(str(exc))
        return
    except Exception as exc:  # noqa: BLE001
        st.error(f"Analysis failed: {exc}")
        return

    created_at = _utc_now_iso()
    if fetch_online and retrieval_sources:
        mode_label = "online:" + ",".join(sorted(retrieval_sources))
    elif fetch_online:
        mode_label = "online"
    elif input_mode == INPUT_MODE_LOCAL:
        mode_label = INPUT_MODE_LOCAL
    else:
        mode_label = INPUT_MODE_JSONL

    meta = RunMeta(
        run_id=run_id,
        query=query.strip(),
        created_at=created_at,
        source_mode=mode_label,
        n_docs=result.n_docs,
        topn=int(topn),
        n_clusters=int(n_clusters),
        summary_sentences=int(summary_sentences),
        retrieval_sources=sorted(retrieval_sources),
    )
    write_run_meta(result.out_dir, meta)
    register_run(meta, result.out_dir)

    st.session_state.selected_run_id = run_id
    st.session_state.show_new_analysis = False
    st.session_state.flash_message = f"Done. Indexed {result.n_docs} documents."
    st.rerun()


def _utc_now_iso() -> str:
    from datetime import timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _render_active_results() -> None:
    flash = st.session_state.pop("flash_message", None)
    if flash:
        st.success(flash)

    partial_warn = st.session_state.pop("partial_fetch_warning", None)
    if partial_warn:
        st.warning(partial_warn, icon="⚠️")

    run_id = st.session_state.selected_run_id
    if not run_id:
        st.info("Select a search from the sidebar or start a new analysis.")
        return
    results_dir = resolve_results_dir(run_id)
    if results_dir is None or not results_dir.exists():
        st.warning("Results for this search could not be found.")
        return
    run = next((r for r in load_index() if r.run_id == run_id), None)
    query_label = run_display_label(run) if run else None
    searched_at = run.created_at if run else None
    _render_results(
        results_dir,
        run_id,
        query_label=query_label,
        searched_at=searched_at,
    )


def main() -> None:
    st.set_page_config(
        page_title="Literature Triage",
        page_icon=":mag:",
        layout="wide",
    )
    _init_session_state()
    load_index()

    st.title("Literature Triage Dashboard")
    _render_sidebar_history()

    if st.session_state.show_new_analysis:
        _render_new_analysis_form()
    else:
        _render_active_results()


if __name__ == "__main__":
    main()
