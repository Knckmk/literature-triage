from __future__ import annotations

import hashlib
import re
from pathlib import Path


def normalize_ws(text: str) -> str:
    """Normalize line endings and collapse excessive whitespace."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def safe_read_text(path: Path) -> str:
    """Read text safely with UTF-8 fallback behavior."""
    return path.read_text(encoding="utf-8", errors="ignore")


def extract_title_and_body(text: str, fallback_title: str) -> tuple[str, str]:
    """
    Title: first non-empty line (markdown headings cleaned if present).
    Body: the remaining lines after the first non-empty line.
    """
    lines = [ln.strip() for ln in text.split("\n")]
    nonempty = [ln for ln in lines if ln]
    if not nonempty:
        return fallback_title, ""

    first = nonempty[0]
    title = re.sub(r"^#{1,6}\s*", "", first).strip()
    title = title if title else fallback_title

    dropped = False
    out: list[str] = []
    for ln in lines:
        if (not dropped) and ln.strip():
            dropped = True
            continue
        out.append(ln)
    body = "\n".join(out).strip()
    return title, body


def word_count(text: str) -> int:
    """Simple token count for lightweight reporting."""
    return len(re.findall(r"\w+", text))


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def split_sentences(text: str, min_tokens: int = 3) -> list[str]:
    """
    Split text into sentences using a lightweight regex heuristic.

    The splitter looks for sentence-ending punctuation followed by whitespace
    and a capital letter or digit (typical sentence boundary). Newlines are
    treated as soft separators so paragraph breaks also become boundaries.
    Sentences with fewer than ``min_tokens`` word tokens are discarded so the
    downstream summarizer is not polluted by headings or stray fragments.
    """
    if not text:
        return []

    flat = re.sub(r"\n+", " ", text).strip()
    if not flat:
        return []

    candidates = _SENTENCE_SPLIT_RE.split(flat)
    sentences: list[str] = []
    for raw in candidates:
        s = raw.strip()
        if not s:
            continue
        if word_count(s) < min_tokens:
            continue
        sentences.append(s)
    return sentences


def corpus_fingerprint(docs_text: list[str]) -> str:
    """
    Build a stable fingerprint of the corpus texts.

    Used to invalidate the TF-IDF cache when any document in the corpus
    changes (added, removed, or edited).
    """
    hasher = hashlib.sha256()
    for text in docs_text:
        hasher.update(str(len(text)).encode("utf-8"))
        hasher.update(b"|")
        hasher.update(text.encode("utf-8", errors="ignore"))
        hasher.update(b"\x1f")
    return hasher.hexdigest()[:16]


def slugify(value: str, max_len: int = 80) -> str:
    """
    Convert an arbitrary string into a filesystem-safe slug.

    Used to derive unique, stable ``doc_id`` values from relative paths
    (for example ``papers/sub/a.md`` -> ``papers__sub__a``).
    """
    if not value:
        return "doc"
    s = value.strip().lower()
    s = re.sub(r"[\\/]+", "__", s)
    s = re.sub(r"[^a-z0-9_.-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        return "doc"
    return s[:max_len]
