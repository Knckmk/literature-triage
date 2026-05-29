from __future__ import annotations

import warnings
from pathlib import Path
from typing import Iterable

from models import Document, PaperMetadata
from storage.jsonl_store import read_jsonl
from utils import (
    extract_title_and_body,
    normalize_ws,
    safe_read_text,
    slugify,
    word_count,
)

try:
    import fitz  # type: ignore

    _PYMUPDF_AVAILABLE = True
except ImportError:
    fitz = None  # type: ignore[assignment]
    _PYMUPDF_AVAILABLE = False

TEXT_EXTS: set[str] = {".txt", ".md"}
PDF_EXTS: set[str] = {".pdf"}
SUPPORTED_EXTS: set[str] = TEXT_EXTS | PDF_EXTS
MIN_BODY_TOKENS = 5
_PDF_WARNED = False


Doc = Document


def iter_docs(corpus_dir: str) -> Iterable[Path]:
    p = Path(corpus_dir)
    if not p.exists() or not p.is_dir():
        raise FileNotFoundError(f"corpus_dir not found or not a directory: {corpus_dir}")

    for fp in sorted(p.rglob("*")):
        if not fp.is_file():
            continue
        if fp.name.startswith("."):
            continue
        if fp.suffix.lower() not in SUPPORTED_EXTS:
            continue
        yield fp


def _make_doc_id(corpus_root: Path, fp: Path, taken: set[str]) -> str:
    """Build a unique, slug-safe doc_id from the file's path relative to the corpus root."""
    try:
        rel = fp.relative_to(corpus_root)
    except ValueError:
        rel = Path(fp.name)
    base = slugify(str(rel.with_suffix("")))
    candidate = base
    suffix = 2
    while candidate in taken:
        candidate = f"{base}_{suffix}"
        suffix += 1
    taken.add(candidate)
    return candidate


def _unique_doc_id(base_value: str, taken: set[str]) -> str:
    base = slugify(base_value) if base_value else "paper"
    candidate = base
    suffix = 2
    while candidate in taken:
        candidate = f"{base}_{suffix}"
        suffix += 1
    taken.add(candidate)
    return candidate


def _read_pdf(fp: Path) -> str:
    """Extract concatenated text from every page of a PDF using PyMuPDF."""
    if fitz is None:
        return ""
    text_parts: list[str] = []
    try:
        with fitz.open(fp) as pdf:
            for page in pdf:
                text_parts.append(page.get_text("text"))
    except Exception as exc:  # noqa: BLE001 - PyMuPDF raises broad errors
        warnings.warn(f"Failed to read PDF {fp.name}: {exc}", stacklevel=2)
        return ""
    return "\n".join(text_parts)


def _read_document(fp: Path) -> str:
    """Dispatch to the right reader based on file extension."""
    global _PDF_WARNED
    suffix = fp.suffix.lower()
    if suffix in TEXT_EXTS:
        return safe_read_text(fp)
    if suffix in PDF_EXTS:
        if not _PYMUPDF_AVAILABLE:
            if not _PDF_WARNED:
                warnings.warn(
                    "Found .pdf files but pymupdf is not installed; skipping them. "
                    "Install with `pip install pymupdf` to enable PDF ingestion.",
                    stacklevel=2,
                )
                _PDF_WARNED = True
            return ""
        return _read_pdf(fp)
    return ""


def load_corpus(corpus_dir: str) -> list[Document]:
    """Read every supported document under ``corpus_dir`` into a document list."""
    corpus_root = Path(corpus_dir).resolve()
    docs: list[Document] = []
    taken_ids: set[str] = set()

    for fp in iter_docs(corpus_dir):
        raw = _read_document(fp)
        raw = normalize_ws(raw)

        try:
            rel_path = str(fp.resolve().relative_to(corpus_root))
        except ValueError:
            rel_path = fp.name

        fallback_title = fp.stem
        title, body = extract_title_and_body(raw, fallback_title=fallback_title)
        wc = word_count(body)

        if wc < MIN_BODY_TOKENS:
            warnings.warn(
                f"Skipping near-empty document (word_count={wc}): {rel_path}",
                stacklevel=2,
            )
            continue

        doc_id = _make_doc_id(corpus_root, fp, taken_ids)
        metadata = PaperMetadata(
            paper_id=doc_id,
            source="local",
            title=title,
            abstract=body,
            authors=[],
            year=None,
            published=None,
            updated=None,
            url=None,
            pdf_url=None,
            doi=None,
            venue=None,
            citation_count=None,
            fields_of_study=[],
            categories=[],
        )
        docs.append(
            Document(
                doc_id=doc_id,
                title=title,
                body=body,
                path=str(fp),
                rel_path=rel_path,
                word_count=wc,
                metadata=metadata,
            )
        )
    return docs


def load_jsonl_corpus(path: str) -> list[Document]:
    """Load retrieved paper metadata JSONL into the internal document model."""
    papers = read_jsonl(path)
    docs: list[Document] = []
    taken_ids: set[str] = set()

    for idx, paper in enumerate(papers, start=1):
        fallback_id = paper.paper_id or paper.title or f"paper_{idx}"
        doc_id = _unique_doc_id(fallback_id, taken_ids)
        title = paper.title or paper.paper_id or f"Paper {idx}"
        abstract = paper.abstract or ""
        docs.append(
            Document(
                doc_id=doc_id,
                title=title,
                body=abstract,
                path=paper.url or paper.pdf_url or "",
                rel_path=paper.paper_id,
                word_count=word_count(abstract),
                metadata=paper,
            )
        )
    return docs


def docs_to_text(docs: list[Document]) -> list[str]:
    """
    Build the per-document text used for TF-IDF.

    Title and body are concatenated so that title tokens influence the score
    too. The same combination is reused by ``cluster.py`` and ``summarize.py``
    to keep features consistent across the pipeline.
    """
    texts: list[str] = []
    for d in docs:
        combined = f"{d.title}\n\n{d.body}".strip()
        texts.append(combined)
    return texts
