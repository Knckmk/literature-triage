#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

python triage.py \
  --corpus_dir examples/corpus \
  --query "2-edge-connected spanning subgraph approximation in subcubic graphs using parity correction" \
  --topn 10 \
  --n_clusters 4 \
  --cache \
  --out_dir results

echo
echo "Pipeline outputs are in ./results"
echo "Launch the dashboard with:  streamlit run dashboard.py"
