from typing import ClassVar

from poller import config, notify, runner, store
from poller.sources.base import PollResult, SermonItem, SourceAdapter


def _item(guid: str) -> SermonItem:
    return SermonItem(
        guid=guid,
        title="Hear and Do",
        raw_title="Hear and Do",
        series=None,
        speaker="Jane Doe",
        published_on="2026-09-06",
        published_at=None,
        episode_url="https://example.org/ep",
        audio_url="https://example.org/ep.mp3",
        blurb="",
    )


class _FakeAdapter(SourceAdapter):
    source = "fake"
    items: ClassVar[list[SermonItem]] = []
    deferred = False

    def poll(self) -> PollResult:
        if self.deferred:
            return PollResult(deferred=True)
        return PollResult(items=list(self.items), excluded=0)


def _church(*, notify_flag: bool) -> config.ChurchConfig:
    return config.ChurchConfig(
        name="fake", rss="https://example.org/feed.xml", enabled=True, notify=notify_flag
    )


def test_poll_church_stores_new_items_and_skips_when_none_are_new(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    monkeypatch.setattr(runner, "ADAPTERS", {"fake": _FakeAdapter})
    _FakeAdapter.items = [_item("g1")]
    _FakeAdapter.deferred = False

    assert runner.poll_church("fake", _church(notify_flag=False), backfill=False) is True
    records = store.load("fake")
    assert set(records) == {"g1"}
    assert records["g1"]["first_seen_at"]

    # A re-poll of the same item must not duplicate or touch first_seen_at.
    first_seen = records["g1"]["first_seen_at"]
    assert runner.poll_church("fake", _church(notify_flag=False), backfill=False) is True
    assert store.load("fake")["g1"]["first_seen_at"] == first_seen


def test_poll_church_defers_without_writing_when_feed_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    monkeypatch.setattr(runner, "ADAPTERS", {"fake": _FakeAdapter})
    _FakeAdapter.items = []
    _FakeAdapter.deferred = True

    assert runner.poll_church("fake", _church(notify_flag=True), backfill=False) is True
    assert store.load("fake") == {}


def test_poll_church_sends_notification_for_new_items_when_notify_is_on(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    monkeypatch.setattr(runner, "ADAPTERS", {"fake": _FakeAdapter})
    _FakeAdapter.items = [_item("g1")]
    _FakeAdapter.deferred = False
    monkeypatch.setenv("NOTIFY_EMAIL_FROM", "alerts@example.org")
    monkeypatch.setenv("NOTIFY_EMAIL_TO", "team@example.org")
    monkeypatch.setenv("RESEND_API_KEY", "re_123")

    sent = []
    monkeypatch.setattr(notify, "send_new_sermons", lambda church, items, cfg: sent.append((church, items)))

    assert runner.poll_church("fake", _church(notify_flag=True), backfill=False) is True
    assert sent == [("fake", [_item("g1")])]
    assert store.load("fake")["g1"]["notified_at"] is not None


def test_poll_church_does_not_notify_when_notify_is_off(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    monkeypatch.setattr(runner, "ADAPTERS", {"fake": _FakeAdapter})
    _FakeAdapter.items = [_item("g1")]
    _FakeAdapter.deferred = False

    sent = []
    monkeypatch.setattr(notify, "send_new_sermons", lambda *a, **k: sent.append(1))

    assert runner.poll_church("fake", _church(notify_flag=False), backfill=False) is True
    assert sent == []
    assert store.load("fake")["g1"]["notified_at"] is None


def test_poll_church_backfill_seeds_ledger_without_notifying(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    monkeypatch.setattr(runner, "ADAPTERS", {"fake": _FakeAdapter})
    _FakeAdapter.items = [_item("g1"), _item("g2")]
    _FakeAdapter.deferred = False

    sent = []
    monkeypatch.setattr(notify, "send_new_sermons", lambda *a, **k: sent.append(1))

    assert runner.poll_church("fake", _church(notify_flag=True), backfill=True) is True
    assert sent == []
    records = store.load("fake")
    assert set(records) == {"g1", "g2"}
    assert records["g1"]["notified_at"] is not None  # marked so a later normal run won't re-send


def test_poll_church_returns_false_when_notification_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    monkeypatch.setattr(runner, "ADAPTERS", {"fake": _FakeAdapter})
    _FakeAdapter.items = [_item("g1")]
    _FakeAdapter.deferred = False
    monkeypatch.setenv("NOTIFY_EMAIL_FROM", "alerts@example.org")
    monkeypatch.setenv("NOTIFY_EMAIL_TO", "team@example.org")
    monkeypatch.setenv("RESEND_API_KEY", "re_123")

    def _boom(*a, **k):
        raise notify.NotifyError("resend is down")

    monkeypatch.setattr(notify, "send_new_sermons", _boom)

    assert runner.poll_church("fake", _church(notify_flag=True), backfill=False) is False
    # The ledger write still happened — discovery is never rolled back for a failed send.
    assert store.load("fake")["g1"]["notified_at"] is None


def test_run_skips_disabled_and_unselected_churches(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    monkeypatch.setattr(runner, "ADAPTERS", {"fake": _FakeAdapter})
    _FakeAdapter.items = [_item("g1")]
    _FakeAdapter.deferred = False
    raw = (
        '{"fake": {"rss": "https://example.org/feed.xml", "enabled": true, "notify": false},'
        ' "off": {"rss": "https://example.org/other.xml", "enabled": false, "notify": false}}'
    )
    monkeypatch.setenv("CHURCHES", raw)

    assert runner.run(church_names=None, backfill=False) is True
    assert set(store.load("fake")) == {"g1"}
    assert store.load("off") == {}
