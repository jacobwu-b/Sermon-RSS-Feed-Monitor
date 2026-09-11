from datetime import UTC, datetime

from poller import store
from poller.net import FeedFetchError
from poller.sources.base import SermonItem
from scripts import backfill_pbc_archive as backfill


def _listing(*, monkeypatch, objects):
    """Patch ``s3_listing.list_objects`` to yield ``objects`` (key, last_modified) tuples."""

    def fake_list_objects(base_url, *, prefix, get, max_pages=1000):
        yield from objects

    monkeypatch.setattr(backfill, "list_objects", fake_list_objects)


def test_run_adds_qualifying_mp3s_and_skips_everything_else(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    objects = [
        ("Main_Service/2019/01/06/20190106.mp3", datetime(2019, 1, 7, 18, 0, tzinfo=UTC)),
        ("Main_Service/2019/01/06/SE_20190106.pdf", datetime(2019, 1, 7, 18, 0, tzinfo=UTC)),
        ("Main_Service/2018/12/30/20181230.mp3", datetime(2018, 12, 31, tzinfo=UTC)),  # before cutoff
        ("Main_Service/not-a-date/weird.mp3", datetime(2020, 1, 1, tzinfo=UTC)),  # malformed path
    ]
    _listing(monkeypatch=monkeypatch, objects=objects)

    result = backfill.run(dry_run=False)

    assert result.non_mp3_skipped == 1
    assert result.before_cutoff_skipped == 1
    assert result.malformed_skipped == 1
    assert len(result.added) == 1

    records = store.load("pbc")
    added = records["pbc-archive:Main_Service/2019/01/06/20190106.mp3"]
    assert added["published_on"] == "2019-01-06"
    assert added["published_at"] == "2019-01-07T18:00:00+00:00"
    assert added["title"] is None
    assert added["series"] is None
    assert added["speaker"] is None
    assert added["episode_url"] is None
    assert added["notified_at"] is not None  # never notify for backfilled history
    assert "Main_Service/2019/01/06/20190106.mp3" in added["audio_url"]


def test_run_is_a_no_op_on_a_second_run_against_the_same_listing(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    objects = [("Main_Service/2019/01/06/20190106.mp3", datetime(2019, 1, 7, 18, 0, tzinfo=UTC))]
    _listing(monkeypatch=monkeypatch, objects=objects)

    backfill.run(dry_run=False)
    first_seen = store.load("pbc")["pbc-archive:Main_Service/2019/01/06/20190106.mp3"]["first_seen_at"]

    second = backfill.run(dry_run=False)

    assert second.added == []
    assert (
        store.load("pbc")["pbc-archive:Main_Service/2019/01/06/20190106.mp3"]["first_seen_at"] == first_seen
    )


def test_run_skips_a_date_already_covered_by_a_live_feed_record(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    live_item = store.item_to_record(
        SermonItem(
            guid="https://pbc.org?enmse_mid=4690",
            title="No Middle Ground",
            raw_title="No Middle Ground",
            series=None,
            speaker=None,
            published_on="2026-09-06",
            published_at=None,
            episode_url="https://pbc.org/sermons?enmse_mid=4690",
            audio_url="https://s3.us-west-2.amazonaws.com/cdn.pbc.org/Main_Service/2026/09/06/x.mp3",
            blurb="",
        ),
        first_seen_at="t0",
        published_at="2026-09-07T18:00:00+00:00",
    )
    store.save("pbc", {live_item["guid"]: live_item})
    objects = [
        ("Main_Service/2026/09/06/Sermon Audio 2026-09-06.mp3", datetime(2026, 9, 7, 18, 0, tzinfo=UTC))
    ]
    _listing(monkeypatch=monkeypatch, objects=objects)

    result = backfill.run(dry_run=False)

    assert result.added == []
    assert result.already_covered_skipped == 1
    assert set(store.load("pbc")) == {"https://pbc.org?enmse_mid=4690"}


def test_dry_run_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    objects = [("Main_Service/2019/01/06/20190106.mp3", datetime(2019, 1, 7, 18, 0, tzinfo=UTC))]
    _listing(monkeypatch=monkeypatch, objects=objects)

    result = backfill.run(dry_run=True)

    assert len(result.added) == 1
    assert store.load("pbc") == {}


def test_main_exits_non_zero_when_the_listing_fetch_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)

    def fake_list_objects(base_url, *, prefix, get, max_pages=1000):
        raise FeedFetchError("boom")
        yield  # pragma: no cover - makes this a generator

    monkeypatch.setattr(backfill, "list_objects", fake_list_objects)

    assert backfill.main([]) == 1
    assert store.load("pbc") == {}


def test_main_exits_zero_and_reports_when_nothing_new_is_found(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(store, "DATA_DIR", tmp_path)
    _listing(monkeypatch=monkeypatch, objects=[])

    assert backfill.main([]) == 0
