"""Configuration read from environment: ``CHURCHES`` and the notify secrets.

All env vars this app reads are listed in ``.env.example``. ``CHURCHES`` is a
GitHub Actions repository *variable* (not a secret) holding one JSON object per
church; ``NOTIFY_EMAIL_FROM``, ``NOTIFY_EMAIL_TO``, and ``RESEND_API_KEY`` are
repository secrets.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or malformed."""


@dataclass(frozen=True)
class ChurchConfig:
    """One church's entry from ``CHURCHES``."""

    name: str
    rss: str
    enabled: bool
    notify: bool


def load_churches(raw: str | None = None) -> dict[str, ChurchConfig]:
    """Parse the ``CHURCHES`` JSON object into ``{name: ChurchConfig}``.

    ``raw`` overrides the live ``CHURCHES`` env var; tests pass it so they never
    depend on process environment. A missing or malformed ``CHURCHES`` is a
    configuration error — there is nothing sensible to poll without it.
    """
    text = raw if raw is not None else os.environ.get("CHURCHES", "")
    if not text.strip():
        raise ConfigError("CHURCHES is not set")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"CHURCHES is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError("CHURCHES must be a JSON object keyed by church name")

    churches: dict[str, ChurchConfig] = {}
    for name, entry in data.items():
        if not isinstance(entry, dict):
            raise ConfigError(f"CHURCHES[{name!r}] must be a JSON object")
        churches[name] = ChurchConfig(
            name=name,
            rss=str(entry.get("rss", "")),
            enabled=bool(entry.get("enabled", False)),
            notify=bool(entry.get("notify", False)),
        )
    return churches


@dataclass(frozen=True)
class NotifyConfig:
    """The Resend email secrets, read once at startup."""

    from_addr: str
    to_addr: str
    api_key: str


def load_notify_config() -> NotifyConfig:
    """Read the three notify secrets, raising if any are missing.

    Only called when a poll actually has something to notify about, so a repo
    that never enables ``notify`` for any church never needs these secrets set.
    """
    missing = [
        var for var in ("NOTIFY_EMAIL_FROM", "NOTIFY_EMAIL_TO", "RESEND_API_KEY") if not os.environ.get(var)
    ]
    if missing:
        raise ConfigError(f"missing required env var(s) for notification: {', '.join(missing)}")
    return NotifyConfig(
        from_addr=os.environ["NOTIFY_EMAIL_FROM"],
        to_addr=os.environ["NOTIFY_EMAIL_TO"],
        api_key=os.environ["RESEND_API_KEY"],
    )
