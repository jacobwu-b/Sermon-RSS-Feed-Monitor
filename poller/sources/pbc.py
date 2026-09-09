"""Peninsula Bible Church: SeriesEngine podcast feed.

PBC organizes its CDN audio by service type; the main Sunday sermon is exactly
an item whose audio is served from the ``Main_Service`` segment and whose
publication day is Sunday.

Two enrichments this adapter does that no other church needs:

- The feed carries no per-episode speaker (it names the church as author, not
  the preacher). ``pbc.org/sermons`` does, in its card markup, keyed by the
  same ``enmse_mid`` the feed uses in its item links — scraped here as a
  best-effort fallback that never blocks discovery if it fails.
- The feed's own ``pubDate`` is a constant nominal value, not the true publish
  time — a placeholder, not real data — so ``published_at`` instead comes from
  the audio enclosure's CDN ``Last-Modified`` header, fetched once per guid.
"""

from __future__ import annotations

import dataclasses
import re
import urllib.parse
from collections.abc import Callable
from datetime import datetime
from typing import Any

import feedparser

from poller.net import FeedFetchError, fetch_feed, http_get, http_head_last_modified
from poller.sources.base import PollResult, SermonItem, SourceAdapter
from poller.sources.common import entry_audio_url, entry_has_identity, parse_pubdate

# A real-browser User-Agent: PBC sits behind a CDN/WAF that can reject bot-shaped agents.
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_MAIN_SERVICE_SEGMENT = "/Main_Service/"
_TITLE_SERIES_SEP = " - "
_SUNDAY = 6
_DEFAULT_SERMONS_URL = "https://pbc.org/sermons/"

# The feed's own <link> does not resolve to the episode on pbc.org's current
# site (it 404s through to the homepage); the sermons page's own card links use
# this query shape against /sermons instead, and that shape does land on the
# specific episode.
_EPISODE_URL_TEMPLATE = "https://pbc.org/sermons?enmse=1&enmse_am=1&enmse_mid={mid}"

# Reads the SeriesEngine "card" markup on pbc.org/sermons for the per-episode
# speaker the feed itself omits, keyed by the same enmse_mid the feed uses.
_SERMONS_PAGE_CARD_RE = re.compile(
    r"<h5>(?P<title>[^<]*)</h5>\s*"
    r'<p class="enmse-speaker-name">(?P<speaker>[^<]*)</p>.*?'
    r"enmse_mid=(?P<mid>\d+)",
    re.DOTALL,
)


def _fetch(url: str) -> bytes:
    return fetch_feed(url, get=lambda target: http_get(target, user_agent=_USER_AGENT))


def _mid_from_url(url: str) -> str | None:
    values = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get("enmse_mid")
    return values[0] if values else None


def parse_sermons_page_speakers(content: bytes) -> dict[str, str]:
    """Map each ``enmse_mid`` on the PBC sermons page to its speaker name."""
    text = content.decode("utf-8", errors="replace")
    return {
        match.group("mid"): match.group("speaker").strip() for match in _SERMONS_PAGE_CARD_RE.finditer(text)
    }


def _split_title(raw_title: str) -> tuple[str, str | None]:
    """Split a ``"{title} - {series}"`` feed title (e.g. "Hear and Do - Luke")."""
    title, sep, series = raw_title.rpartition(_TITLE_SERIES_SEP)
    if not sep:
        return raw_title, None
    return title, series


def episode_url_from_link(raw_link: str) -> str:
    """The episode link to publish: the feed's ``enmse_mid`` rebuilt against ``/sermons``."""
    mid = _mid_from_url(raw_link)
    return _EPISODE_URL_TEMPLATE.format(mid=mid) if mid is not None else raw_link


def _entry_to_item(entry: Any) -> tuple[SermonItem, int, str | None]:
    """Convert a feedparser entry into ``(item, weekday, mid)``."""
    raw_title = (entry.get("title") or "").strip()
    title, series = _split_title(raw_title)
    published_on, weekday = parse_pubdate(entry.get("published"))
    episode_url = episode_url_from_link(entry.get("link", ""))
    item = SermonItem(
        guid=entry.get("id", ""),
        title=title,
        raw_title=raw_title,
        series=series,
        speaker=None,  # filled in from the sermons-page scrape below, if found
        published_on=published_on,
        published_at=None,  # PBC's own pubDate is a placeholder; see module docstring
        episode_url=episode_url,
        audio_url=entry_audio_url(entry),
        blurb=(entry.get("summary") or "").strip(),
    )
    return item, weekday, _mid_from_url(episode_url)


def _parse(content: bytes) -> tuple[list[tuple[SermonItem, int, str | None]], int]:
    parsed = feedparser.parse(content)
    items: list[tuple[SermonItem, int, str | None]] = []
    skipped = 0
    for entry in parsed.entries:
        if not entry_has_identity(entry):
            skipped += 1
            continue
        items.append(_entry_to_item(entry))
    return items, skipped


def is_main_sunday_sermon(audio_url: str, weekday: int) -> bool:
    """Whether an item is PBC's main Sunday sermon: ``Main_Service`` audio + Sunday."""
    return _MAIN_SERVICE_SEGMENT in audio_url and weekday == _SUNDAY


class PbcAdapter(SourceAdapter):
    """Ingest Peninsula Bible Church sermons from the SeriesEngine feed."""

    source = "pbc"

    def __init__(
        self,
        *,
        url: str,
        sermons_url: str = _DEFAULT_SERMONS_URL,
        fetch_last_modified: Callable[[str], datetime | None] = http_head_last_modified,
    ) -> None:
        super().__init__(url=url)
        self._sermons_url = sermons_url
        self._fetch_last_modified = fetch_last_modified

    def _fetch_speakers(self) -> dict[str, str]:
        """Best-effort mid-to-speaker mapping; never blocks discovery on failure."""
        try:
            content = fetch_feed(
                self._sermons_url,
                get=lambda target: http_get(target, user_agent=_USER_AGENT),
            )
        except FeedFetchError:
            return {}
        return parse_sermons_page_speakers(content)

    def resolve_published_at(self, item: SermonItem) -> datetime | None:
        """The real publish instant for a newly-discovered item.

        Worth its cost only the first time a guid is seen — the runner calls
        this for new items only, so the CDN HEAD is a one-time cost per sermon
        rather than one per poll (PBC's own pubDate is a placeholder; see
        module docstring).
        """
        return self._fetch_last_modified(item.audio_url)

    def poll(self) -> PollResult:
        try:
            content = _fetch(self.url)
        except FeedFetchError:
            return PollResult(deferred=True)

        triples, id_less = _parse(content)
        included: list[SermonItem] = []
        excluded = id_less
        for item, weekday, _mid in triples:
            if is_main_sunday_sermon(item.audio_url, weekday):
                included.append(item)
            else:
                excluded += 1

        speakers = self._fetch_speakers()
        enriched: list[SermonItem] = []
        for item in included:
            mid = _mid_from_url(item.episode_url)
            speaker = speakers.get(mid) if mid is not None else None
            enriched.append(dataclasses.replace(item, speaker=speaker))

        return PollResult(items=enriched, excluded=excluded)
