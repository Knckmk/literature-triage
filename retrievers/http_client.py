from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_TIMEOUT = 60
DEFAULT_USER_AGENT = "LiteratureTriageTool/1.0 (academic research; mailto:ahmetkaancakmak@ogrenci.beykoz.edu.tr)"
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 5.0

_last_arxiv_request_at: float = 0.0
_last_openalex_request_at: float = 0.0
ARXIV_MIN_INTERVAL = 3.0
OPENALEX_MIN_INTERVAL = 0.2


def get_json(
    url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    rate_limit: str | None = None,
    max_retries: int = MAX_RETRIES,
) -> Any:
    """GET URL and parse JSON response with retries on 429 and timeouts."""
    payload = get_bytes(
        url,
        timeout=timeout,
        headers=headers,
        rate_limit=rate_limit,
        max_retries=max_retries,
    )
    return json.loads(payload.decode("utf-8"))


def get_bytes(
    url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    rate_limit: str | None = None,
    max_retries: int = MAX_RETRIES,
) -> bytes:
    """GET URL and return raw bytes with retries on 429 and timeouts."""
    if rate_limit == "arxiv":
        _wait_for_arxiv_slot()
    elif rate_limit == "openalex":
        _wait_for_openalex_slot()

    merged_headers = {"User-Agent": DEFAULT_USER_AGENT}
    if headers:
        merged_headers.update(headers)

    attempts = max(1, int(max_retries))
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers=merged_headers)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code in {429, 503} and attempt < attempts - 1:
                time.sleep(RETRY_BACKOFF_BASE * (2**attempt))
                continue
            raise
        except (TimeoutError, urllib.error.URLError) as exc:
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(RETRY_BACKOFF_BASE * (2**attempt))
                continue
            raise

    if last_error is not None:
        raise last_error
    raise RuntimeError("HTTP request failed without a specific error.")


def _wait_for_arxiv_slot() -> None:
    global _last_arxiv_request_at
    _wait_for_slot(_last_arxiv_request_at, ARXIV_MIN_INTERVAL)
    _last_arxiv_request_at = time.monotonic()


def _wait_for_openalex_slot() -> None:
    global _last_openalex_request_at
    _wait_for_slot(_last_openalex_request_at, OPENALEX_MIN_INTERVAL)
    _last_openalex_request_at = time.monotonic()


def _wait_for_slot(last_at: float, min_interval: float) -> None:
    now = time.monotonic()
    elapsed = now - last_at
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
