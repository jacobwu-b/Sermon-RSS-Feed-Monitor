from poller.sources.westgate import _parse_title, is_main_sunday_sermon


def test_parse_title_extracts_series_title_and_date():
    title, series, service_date = _parse_title(
        "The Gospel of John (Part 2) | To Whom Shall We Go | August 16, 2026"
    )
    assert title == "To Whom Shall We Go"
    assert series == "The Gospel of John (Part 2)"
    assert service_date.isoformat() == "2026-08-16"


def test_parse_title_without_trailing_date_is_unclassifiable():
    title, series, service_date = _parse_title("An Old Archive Sermon")
    assert service_date is None
    assert series is None
    assert title == "An Old Archive Sermon"


def test_is_main_sunday_sermon_requires_sunday_weekday():
    assert is_main_sunday_sermon("Series | Title | August 16, 2026", 6) is True
    assert is_main_sunday_sermon("Series | Title | August 17, 2026", 0) is False


def test_is_main_sunday_sermon_excludes_nextgen_program():
    assert is_main_sunday_sermon("NextGen Sunday | Title | August 16, 2026", 6) is False


def test_is_main_sunday_sermon_excludes_unparseable_title():
    assert is_main_sunday_sermon("An Old Archive Sermon", -1) is False
