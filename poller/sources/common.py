"""Feed-parsing helpers shared by every adapter (pubdate parsing, identity, enclosure)."""

from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any


def parse_pubdate(raw: str | None) -> tuple[str, int]:
    """Parse an RFC-822 ``pubDate`` into ``(YYYY-MM-DD, weekday)`` in its own timezone.

    ``weekday`` uses the ``email.utils`` convention: Monday=0 … Sunday=6. A
    missing or unparseable date yields ``("", -1)`` so the item is never
    mistaken for a Sunday.
    """
    if not raw:
        return "", -1
    try:
        when = parsedate_to_datetime(raw)
    except (ValueError, TypeError):
        return "", -1
    return when.date().isoformat(), when.weekday()


def parse_pubdate_at(raw: str | None) -> datetime | None:
    """Parse an RFC-822 ``pubDate`` into its full instant, or ``None`` if unusable."""
    if not raw:
        return None
    try:
        when = parsedate_to_datetime(raw)
    except (ValueError, TypeError):
        return None
    return when if when.tzinfo is not None else when.replace(tzinfo=UTC)


def entry_audio_url(entry: Any) -> str:
    """Return the first enclosure URL on a feed entry, or ``""`` if none is present."""
    for enclosure in entry.get("enclosures", []):
        href = enclosure.get("href")
        if href:
            return str(href)
    return ""


def entry_has_identity(entry: Any) -> bool:
    """Whether a feed entry carries a usable id (a ``<guid>``, or its ``<link>`` fallback).

    feedparser derives ``entry.id`` from ``<guid>``, falling back to ``<link>``;
    an item with neither yields ``""``. Every id-less item in a feed would
    otherwise collapse onto the same (or, for a namespaced adapter, prefix-only)
    key on upsert, so adapters must skip these before building a
    :class:`~poller.sources.base.SermonItem`.
    """
    return bool(entry.get("id", ""))
