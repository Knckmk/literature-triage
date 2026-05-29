PYTHON ?= python
PIP ?= $(PYTHON) -m pip
QUERY ?= 2-edge-connected spanning subgraph approximation in subcubic graphs

.PHONY: install run-demo dashboard retrieve-online test clean

install:
	$(PIP) install -r requirements.txt

run-demo:
	$(PYTHON) triage.py --corpus_dir examples/corpus --query "$(QUERY)" --topn 10 --n_clusters 4 --cache

dashboard:
	.venv/bin/streamlit run dashboard.py

retrieve-online:
	.venv/bin/python retrieve_online.py --query "$(QUERY)" --max_results 50 --out data/online_corpus.jsonl

test:
	$(PYTHON) -m pytest

clean:
	$(PYTHON) -c "import pathlib, shutil; roots=['results','tmp_results','.pytest_cache','.mypy_cache','.ruff_cache']; [shutil.rmtree(p, ignore_errors=True) for p in roots]; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]; [p.unlink(missing_ok=True) for p in pathlib.Path('.').rglob('*.pyc')]; [p.unlink(missing_ok=True) for p in pathlib.Path('.').rglob('.DS_Store')]; shutil.rmtree('__MACOSX', ignore_errors=True)"
