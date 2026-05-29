# AI-Assisted Literature Triage Tool

This project ranks, clusters, summarizes, and reports on a literature corpus for
a research query. The current implementation is fully local: it reads documents
from a folder and uses classic information retrieval and machine learning
techniques instead of an LLM.

## Modes

The project is organized around two modes:

1. Local corpus triage, available now.
   - Reads `.txt`, `.md`, and optional `.pdf` files from a local directory.
   - Ranks documents with TF-IDF and cosine similarity.
   - Clusters documents with KMeans.
   - Extracts cluster keywords and query-focused extractive summaries.
   - Writes CSV, JSON, and Markdown outputs under `results/`.
2. Online retrieval mode, planned.
   - Retrieves paper metadata from online sources before running the same
     triage workflow.
   - arXiv retrieval is available now.

The Turkish walkthrough is available in [REHBER.md](REHBER.md).

## Project Layout

```text
.
|-- triage.py            # CLI entry point for the full pipeline
|-- ingest.py            # Corpus loading for txt, md, and pdf files
|-- vectorize.py         # Document-level TF-IDF vectorization
|-- rank.py              # Query ranking with cosine similarity
|-- cluster.py           # KMeans clustering and cluster keywords
|-- summarize.py         # Query-focused extractive summaries
|-- report.py            # Markdown report generation
|-- dashboard.py         # Streamlit dashboard for generated results
|-- utils.py             # Shared helpers
|-- examples/
|   |-- corpus/          # Demo corpus
|   `-- run_example.sh
`-- results/             # Generated outputs, ignored by git
```

## Setup

Create and activate a virtual environment, then install the project
dependencies.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If you have `make` installed, you can use:

```bash
make install
```

For development tools:

```bash
pip install -e ".[dev]"
```

## Local Corpus Mode

Run the triage pipeline against local `.txt`, `.md`, or `.pdf` files:

```bash
python triage.py --corpus_dir examples/corpus --query "2-edge-connected spanning subgraph approximation in subcubic graphs" --topn 10 --n_clusters 4 --cache
```

The equivalent Make command is:

```bash
make run-demo
```

The original CLI behavior is still supported:

```bash
python triage.py --corpus_dir examples/corpus --query "your research question"
```

## arXiv Retrieval Mode

Retrieve arXiv metadata into JSONL:

```bash
python retrieve_arxiv.py --query "graphic TSP approximation parity correction" --max_results 50 --out data/arxiv_corpus.jsonl
```

Run triage directly on the retrieved JSONL corpus:

```bash
python triage.py --jsonl data/arxiv_corpus.jsonl --query "graphic TSP approximation parity correction" --topn 10 --n_clusters 4
```

Combined workflow:

```bash
python retrieve_arxiv.py --query "graphic TSP approximation parity correction" --max_results 50 --out data/arxiv_corpus.jsonl
python triage.py --jsonl data/arxiv_corpus.jsonl --query "graphic TSP approximation parity correction" --topn 10 --n_clusters 4
streamlit run dashboard.py
```

## Dashboard

Open the Streamlit dashboard:

```bash
streamlit run dashboard.py
```

Or:

```bash
make dashboard
```

The dashboard is the primary way to use the tool. Open it with
`streamlit run dashboard.py` or `make dashboard`.

- **New analysis** (main panel): fetch papers from selected online sources
  (arXiv, OpenAlex), run ranking, clustering, and summaries.
  Each run is saved automatically.
- **Saved results** (sidebar): ChatGPT-style search history (up to 20 runs).
  Click a past query to reopen its full results.

Run outputs are stored under `results/runs/<run_id>/` with an index at
`results/index.json`.

## Online Retrieval (arXiv + OpenAlex)

The dashboard **Advanced options** panel lets you choose which online sources
to query (both are enabled by default). Results are merged and deduplicated
(DOI / arXiv ID / title) before analysis.

| Source | API key | Notes |
| --- | --- | --- |
| arXiv | No | Respect ~1 request / 3 seconds |
| OpenAlex | No | Set `OPENALEX_MAILTO` in `.env` (see `.env.example`) |

CLI example (all sources):

```bash
python retrieve_online.py --query "federated learning differential privacy" --sources arxiv,openalex --max_results 50 --out data/online_corpus.jsonl
```

arXiv-only (legacy CLI still works):

```bash
python retrieve_arxiv.py --query "graphic TSP approximation parity correction" --max_results 50 --out data/arxiv_corpus.jsonl
```

Then run triage on the JSONL corpus:

```bash
python triage.py --jsonl data/online_corpus.jsonl --query "your question" --topn 10 --n_clusters 4
```

The output is JSONL: one `PaperMetadata` record per line, including merged
`sources` when a paper appears in multiple APIs.

## Expected Outputs

The pipeline writes generated files to `results/` by default.

| File | Purpose |
| --- | --- |
| `ranking.csv` | Ranked top-N documents with score, metadata, matched terms, and snippets. |
| `ranking.json` | JSON version of the ranking output with explainability fields. |
| `clusters.csv` | Cluster assignment and centroid distance for each document. |
| `cluster_keywords.json` | Top TF-IDF keywords for each cluster. |
| `cluster_summaries.json` | Demo-ready cluster labels, keywords, counts, and representative docs. |
| `summaries.json` | Query-focused summaries, snippets, matched terms, and best matching sentences. |
| `report.md` | Human-readable Markdown report. |
| `cache/tfidf_<hash>.joblib` | Optional TF-IDF cache when `--cache` is enabled. |

`results/` is ignored by git because it contains generated artifacts.

## CLI Options

```text
--corpus_dir          Local corpus directory. Use exactly one of --corpus_dir or --jsonl.
--jsonl               JSONL paper metadata corpus. Use exactly one of --corpus_dir or --jsonl.
--query               Research question or search query. Required.
--topn                Number of top documents to output. Default: 10.
--n_clusters          KMeans cluster count. Default: 4.
--top_keywords        Keywords per cluster. Default: 10.
--summary_sentences   Summary sentence count. Default: 3.
--steps               Pipeline steps: rank,cluster,summarize,report or all.
--cache               Cache TF-IDF artifacts under <out_dir>/cache.
--out_dir             Output directory. Default: results.
```

Partial pipeline example:

```bash
python triage.py --corpus_dir examples/corpus --query "approximation algorithms" --steps rank,cluster
```

## Maintenance Commands

```bash
make test
make clean
```

`make clean` removes generated outputs, Python bytecode, and local tool caches.
