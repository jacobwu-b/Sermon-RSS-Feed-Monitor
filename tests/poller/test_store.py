from poller import store
from poller.sources.base import SermonItem


def _item(guid: str = "g1") -> SermonItem:
    return SermonItem(
        guid=guid,
        title="Hear and Do",
        raw_title="Hear and Do - Luke",
        series="Luke",
        speaker="Jane Doe",
        published_on="2026-09-06",
        published_at=None,
        episode_url="https://example.org/ep1",
        audio_url="https://example.org/ep1.mp3",
        blurb="A sermon on Luke.",
    )


def test_load_returns_empty_dict_for_a_church_with_no_ledger_yet(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    assert store.load("menlo") == {}


def test_save_then_load_round_trips_a_record(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    record = store.item_to_record(_item(), first_seen_at="2026-09-06T12:00:00+00:00", published_at=None)
    store.save("menlo", {"g1": record})

    loaded = store.load("menlo")
    assert loaded == {"g1": record}
    assert loaded["g1"]["title"] == "Hear and Do"
    assert loaded["g1"]["speaker"] == "Jane Doe"
    assert loaded["g1"]["notified_at"] is None


def test_item_to_record_discards_empty_strings_as_placeholders():
    item = _item()
    item = item.__class__(**{**item.__dict__, "episode_url": "", "blurb": ""})
    record = store.item_to_record(item, first_seen_at="now", published_at=None)
    assert record["episode_url"] is None
    assert record["blurb"] is None


def test_save_is_idempotent_and_stable_on_key_order(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    record_b = store.item_to_record(_item("b"), first_seen_at="t1", published_at=None)
    record_a = store.item_to_record(_item("a"), first_seen_at="t2", published_at=None)
    store.save("menlo", {"b": record_b, "a": record_a})

    path = tmp_path / "menlo.json"
    first_write = path.read_text(encoding="utf-8")
    store.save("menlo", store.load("menlo"))
    assert path.read_text(encoding="utf-8") == first_write
    assert list(store.load("menlo").keys()) == ["a", "b"]
