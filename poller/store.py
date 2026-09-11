"""The per-church JSON ledger: one file per church, keyed by guid.

Each record keeps every real field the source gave us — link, title, speaker,
series, the service date, the instant the feed first made it available (when
known), and the instant this poller first retrieved it — and nothing else.
Upsert is idempotent on guid: a re-poll of an already-known sermon never
duplicates it or clobbers its ``first_seen_at``/``published_at``. Every write
re-sorts the whole file newest-``published_on``-first, so opening a ledger
always shows the latest sermon at the top.
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


def _ordered_items(records: dict[str, dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    """Newest-``published_on`` first; records missing it sort after every dated one.

    Ties (same ``published_on``, or no ``published_on`` at all) break by
    ``published_at`` then guid, both ascending — Python's sort is stable, so
    sorting by guid first and then by date leaves equal-date groups in
    guid-ascending order.
    """
    dated = [(guid, r) for guid, r in records.items() if r.get("published_on")]
    undated = [(guid, r) for guid, r in records.items() if not r.get("published_on")]
    undated.sort(key=lambda kv: kv[0])
    dated.sort(key=lambda kv: kv[0])
    dated.sort(key=lambda kv: (kv[1]["published_on"], kv[1].get("published_at") or ""), reverse=True)
    return dated + undated


def save(church: str, records: dict[str, dict[str, Any]]) -> None:
    """Write a church's ledger back, newest ``published_on`` first, for an easy-to-scan file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = _record_path(church)
    ordered = dict(_ordered_items(records))
    with path.open("w", encoding="utf-8") as f:
        json.dump(ordered, f, indent=2, ensure_ascii=False)
        f.write("\n")


def item_to_record(item: SermonItem, *, first_seen_at: str, published_at: str | None) -> dict[str, Any]:
    """Build the JSON record for a newly-discovered item."""
    return {
        "guid": item.guid,
        "title": item.title or None,
        "raw_title": item.raw_title or None,
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
