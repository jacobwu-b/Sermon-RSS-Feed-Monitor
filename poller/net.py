"""Shared feed-fetch transport: retries, scheme guard, and a body size cap.

Every adapter fetches its feed (and, for PBC, an auxiliary HTML page and a HEAD
request) through this module so the hardening lives in one place. The feed URLs
themselves are fixed, operator-configured values from ``CHURCHES``, not
attacker-controlled input, so the guard here is a simple defense-in-depth cap
rather than a full SSRF-hardened opener.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

DEFAULT_USER_AGENT = "sermon-rss-monitor/1.0 (+https://github.com/jacobwu-b/Sermon-RSS-Feed-Monitor)"
_ALLOWED_SCHEMES = frozenset({"http", "https"})
_MAX_BODY_BYTES = 32 * 1024 * 1024  # a podcast RSS feed is a few MB at most
_TIMEOUT = 30
_ATTEMPTS = 3
_BACKOFF_BASE = 1.0


class FeedFetchError(RuntimeError):
    """Raised when a URL cannot be fetched after retries, or is unsafe to fetch."""


def http_get(url: str, *, user_agent: str = DEFAULT_USER_AGENT) -> bytes:
    """Fetch ``url`` over HTTP(S) and return the raw body (the mocked boundary)."""
    scheme = urllib.parse.urlsplit(url).scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise FeedFetchError(f"refusing to fetch non-http(s) url: {url!r}")
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
            body = response.read(_MAX_BODY_BYTES + 1)
    except (urllib.error.URLError, OSError) as exc:
        raise FeedFetchError(f"fetch failed for {url!r}: {exc}") from exc
    if len(body) > _MAX_BODY_BYTES:
        raise FeedFetchError(f"body exceeds {_MAX_BODY_BYTES}-byte cap: {url!r}")
    return body


def http_head_last_modified(url: str, *, user_agent: str = DEFAULT_USER_AGENT) -> datetime | None:
    """HEAD ``url`` and return its ``Last-Modified`` instant, or ``None`` if unusable.

    Never raises: a missing header, non-2xx response, or network error all yield
    ``None`` since this is enrichment (PBC's real publish instant), never
    load-bearing for discovery.
    """
    scheme = urllib.parse.urlsplit(url).scheme.lower()
    if scheme not in _ALLOWED_SCHEMES or not url:
        return None
    request = urllib.request.Request(url, headers={"User-Agent": user_agent}, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
            raw = response.headers.get("Last-Modified")
    except (urllib.error.URLError, OSError):
        return None
    if not raw:
        return None
    try:
        when = parsedate_to_datetime(raw)
    except (ValueError, TypeError):
        return None
    return when if when.tzinfo is not None else when.replace(tzinfo=UTC)


def fetch_feed(
    url: str,
    *,
    get: Callable[[str], bytes] = http_get,
    sleep: Callable[[float], None] = time.sleep,
    attempts: int = _ATTEMPTS,
    backoff_base: float = _BACKOFF_BASE,
) -> bytes:
    """Fetch a URL, retrying transient failures with exponential backoff.

    Exhausting all attempts raises :class:`FeedFetchError` so the caller can
    defer this source to the next scheduled run rather than crash the poll.
    """
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return get(url)
        except FeedFetchError as exc:
            last_error = exc
            if attempt < attempts:
                sleep(backoff_base * 2 ** (attempt - 1))
    raise FeedFetchError(f"fetch failed after {attempts} attempts: {last_error}") from last_error


def now() -> str:
    """Current UTC instant as an ISO-8601 string — the "first retrieved" timestamp."""
    return datetime.now(UTC).isoformat()
