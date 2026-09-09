"""The poll entry point: fetch every enabled church, ledger new sermons, notify.

One run touches every church ``CHURCHES`` marks ``enabled`` (or the subset
named by ``--church``), independently — one church's feed being down, or its
notification failing, never stops the others from being polled and recorded.
``--backfill`` seeds a church's ledger from its full feed history without
sending any notification for what it adds, so a first run (or a run after
adding a new church) doesn't blast an inbox with years of back-catalog.
"""

from __future__ import annotations

import argparse
import logging
import sys

from poller import config, notify, store
from poller.net import now
from poller.sources import ADAPTERS

logger = logging.getLogger("poller")


def poll_church(name: str, entry: config.ChurchConfig, *, backfill: bool) -> bool:
    """Poll one church, ledger any new sermons, and notify if configured.

    Returns ``True`` on success (including "feed unavailable, deferred" — that
    is an expected, retried-next-run outcome, not a failure of this run).
    """
    adapter_cls = ADAPTERS.get(name)
    if adapter_cls is None:
        logger.warning("%s: no adapter registered for this church; skipping", name)
        return True

    adapter = adapter_cls(url=entry.rss)
    result = adapter.poll()
    if result.deferred:
        logger.warning("%s: feed unavailable, deferring to next run", name)
        return True

    records = store.load(name)
    retrieved_at = now()
    new_items = [item for item in result.items if item.guid not in records]
    for item in new_items:
        published_at = adapter.resolve_published_at(item)
        records[item.guid] = store.item_to_record(
            item,
            first_seen_at=retrieved_at,
            published_at=published_at.isoformat() if published_at is not None else None,
        )

    logger.info(
        "%s: %d discovered, %d new, %d excluded",
        name,
        len(result.items),
        len(new_items),
        result.excluded,
    )

    if not new_items:
        return True

    if backfill:
        # Backfill seeds history without emailing — mark it already-notified so
        # a later normal run never sends for these.
        for item in new_items:
            records[item.guid]["notified_at"] = retrieved_at
        store.save(name, records)
        return True

    store.save(name, records)

    if not entry.notify:
        return True

    try:
        notify_cfg = config.load_notify_config()
        notify.send_new_sermons(name, new_items, notify_cfg)
    except (config.ConfigError, notify.NotifyError) as exc:
        logger.error(
            "%s: notification failed for %d new sermon(s): %s",
            name,
            len(new_items),
            exc,
        )
        return False

    for item in new_items:
        records[item.guid]["notified_at"] = now()
    store.save(name, records)
    return True


def run(*, church_names: list[str] | None, backfill: bool) -> bool:
    """Poll every selected, enabled church. Returns ``True`` iff all succeeded."""
    churches = config.load_churches()
    selected = {
        name: entry
        for name, entry in churches.items()
        if entry.enabled and (church_names is None or name in church_names)
    }
    if not selected:
        logger.warning("no enabled churches matched the selection; nothing to poll")
        return True

    all_ok = True
    for name, entry in selected.items():
        try:
            ok = poll_church(name, entry, backfill=backfill)
        except Exception:
            logger.exception("%s: poll crashed unexpectedly", name)
            ok = False
        all_ok = all_ok and ok
    return all_ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--church",
        action="append",
        dest="churches",
        help="Only poll this church (repeatable). Default: every enabled church.",
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Seed the ledger from the full feed history without sending notifications.",
    )
    parser.add_argument("--verbose", action="store_true", help="Debug-level logging.")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    ok = run(church_names=args.churches, backfill=args.backfill)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
