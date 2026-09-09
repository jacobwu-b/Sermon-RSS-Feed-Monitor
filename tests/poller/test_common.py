from poller.sources.common import entry_audio_url, entry_has_identity, parse_pubdate, parse_pubdate_at


def test_parse_pubdate_returns_date_and_weekday():
    on, weekday = parse_pubdate("Sun, 06 Sep 2026 10:00:00 -0700")
    assert on == "2026-09-06"
    assert weekday == 6


def test_parse_pubdate_missing_value_is_never_sunday():
    assert parse_pubdate(None) == ("", -1)


def test_parse_pubdate_malformed_value_is_never_sunday():
    assert parse_pubdate("not a date") == ("", -1)


def test_parse_pubdate_at_returns_a_tz_aware_instant():
    when = parse_pubdate_at("Sun, 06 Sep 2026 10:00:00 -0700")
    assert when is not None
    assert when.tzinfo is not None


def test_parse_pubdate_at_missing_value_is_none():
    assert parse_pubdate_at(None) is None


def test_entry_audio_url_returns_first_enclosure():
    entry = {"enclosures": [{"href": "https://example.org/a.mp3"}, {"href": "https://example.org/b.mp3"}]}
    assert entry_audio_url(entry) == "https://example.org/a.mp3"


def test_entry_audio_url_with_no_enclosures_is_empty():
    assert entry_audio_url({}) == ""


def test_entry_has_identity_true_when_id_present():
    assert entry_has_identity({"id": "guid-1"}) is True


def test_entry_has_identity_false_when_id_missing():
    assert entry_has_identity({}) is False
