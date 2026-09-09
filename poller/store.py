"""The per-church JSON ledger: one file per church, keyed by guid.

Each record keeps every real field the source gave us — link, title, speaker,
series, the service date, the instant the feed first made it available (when
known), and the instant this poller first retrieved it — and nothing else.
Upsert is idempotent on guid: a re-poll of an already-known sermon never
duplicates it or clobbers its ``first_seen_at``/``published_at``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from poller.sources.base import SermonItem

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _record_path(church: str) -> Path:
    return DATA_DIR / f"{church}.json"


def load(church: str) -> dict[str, dict[str, Any]]:
    """Load a church's ledger as ``{guid: record}``, or ``{}`` if it has none yet."""
    path = _record_path(church)
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save(church: str, records: dict[str, dict[str, Any]]) -> None:
    """Write a church's ledger back, sorted by guid for a stable, reviewable diff."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = _record_path(church)
    ordered = dict(sorted(records.items()))
    with path.open("w", encoding="utf-8") as f:
        json.dump(ordered, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")


def item_to_record(item: SermonItem, *, first_seen_at: str, published_at: str | None) -> dict[str, Any]:
    """Build the JSON record for a newly-discovered item."""
    return {
        "guid": item.guid,
        "title": item.title,
        "raw_title": item.raw_title,
        "series": item.series,
        "speaker": item.speaker,
        "published_on": item.published_on or None,
        "published_at": published_at,
        "episode_url": item.episode_url or None,
        "audio_url": item.audio_url or None,
        "blurb": item.blurb or None,
        "first_seen_at": first_seen_at,
        "notified_at": None,
    }
