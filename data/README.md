# Sermon ledger

One JSON file per church (`<church>.json`, matching its `CHURCHES` key),
written and updated only by [`poller/runner.py`](../poller/runner.py). Each
file is a JSON object keyed by the feed's own guid:

```json
{
  "<guid>": {
    "guid": "...",
    "title": "Hear and Do",
    "raw_title": "Hear and Do - Luke",
    "series": "Luke",
    "speaker": "Jane Doe",
    "published_on": "2026-09-06",
    "published_at": "2026-09-06T17:03:00+00:00",
    "episode_url": "https://example.org/sermons/hear-and-do",
    "audio_url": "https://example.org/audio/hear-and-do.mp3",
    "blurb": "A sermon on Luke 10.",
    "first_seen_at": "2026-09-06T17:05:12.345678+00:00",
    "notified_at": "2026-09-06T17:05:13.012345+00:00"
  }
}
```

A field is `null` when the source genuinely doesn't carry it, or when the only
value available is a placeholder rather than real data (see each adapter's
module docstring for churches where that applies) — never a fabricated
default. `first_seen_at` is when this poller first retrieved the record;
`published_at` is when the source itself first made it available, when that's
knowable. `notified_at` is set once an email has gone out for the record (or,
for a `--backfill` run, once it's been seeded without one) so a re-poll never
sends twice.

These files are committed automatically by
[`.github/workflows/poll.yml`](../.github/workflows/poll.yml) — do not edit
them by hand.
