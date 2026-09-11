"""Paginated ``ListObjectsV2`` XML listing for a public, unauthenticated S3 bucket.

Used only by ``scripts/backfill_pbc_archive.py`` to enumerate ``cdn.pbc.org``
(see ADR-0003 for why: PBC's RSS feed is hard-capped at 10 items and the
bucket behind its own audio URLs is public and listable). Fetches each page
through the caller's ``get`` (normally :func:`poller.net.fetch_feed`) so the
shared retry/scheme-guard/body-cap transport applies here too — this module
only owns the XML pagination and parsing.
"""

from __future__ import annotations

import urllib.parse
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterator
from datetime import datetime

_S3_NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"


class S3ListingError(RuntimeError):
    """Raised when a listing page can't be parsed."""


def _text(parent: ET.Element, tag: str) -> str | None:
    child = parent.find(f"{_S3_NS}{tag}")
    return child.text if child is not None else None


def _parse_last_modified(raw: str) -> datetime:
    # Python 3.11+'s fromisoformat accepts a literal "Z" directly.
    return datetime.fromisoformat(raw)


def _parse_page(content: bytes) -> tuple[list[tuple[str, datetime]], str | None]:
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise S3ListingError(f"malformed ListObjectsV2 XML: {exc}") from exc

    is_truncated = _text(root, "IsTruncated")
    if is_truncated is None:
        raise S3ListingError("ListObjectsV2 response missing IsTruncated")

    items: list[tuple[str, datetime]] = []
    for contents in root.findall(f"{_S3_NS}Contents"):
        key = _text(contents, "Key")
        last_modified = _text(contents, "LastModified")
        if key is None or last_modified is None:
            raise S3ListingError("ListObjectsV2 <Contents> missing Key or LastModified")
        items.append((key, _parse_last_modified(last_modified)))

    next_token = _text(root, "NextContinuationToken") if is_truncated == "true" else None
    return items, next_token


def list_objects(
    base_url: str,
    *,
    prefix: str,
    get: Callable[[str], bytes],
    max_pages: int = 1000,
) -> Iterator[tuple[str, datetime]]:
    """Yield ``(key, last_modified)`` for every object under ``prefix``, paginating.

    ``max_pages`` is a defensive ceiling (a public bucket's own pagination
    bug or an infinite continuation-token loop should not hang this
    forever) — a listing this deep would already be a surprise worth
    investigating, not a silent truncation.
    """
    token: str | None = None
    for _ in range(max_pages):
        params = {"list-type": "2", "prefix": prefix}
        if token is not None:
            params["continuation-token"] = token
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        items, token = _parse_page(get(url))
        yield from items
        if token is None:
            return
    raise S3ListingError(f"exceeded max_pages={max_pages} without reaching the end of the listing")
