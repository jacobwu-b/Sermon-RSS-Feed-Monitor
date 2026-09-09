from poller.sources.lakepointe import _split_title, is_main_sunday_sermon

_SUNDAY = 6
_MONDAY = 0


def test_split_title_three_segments():
    assert _split_title("Grace | Romans | Pastor Josh") == ("Grace", "Romans", "Pastor Josh")


def test_split_title_archive_format_with_no_separator():
    assert _split_title("Grace") == ("Grace", None, None)


def test_is_main_sunday_sermon_true_for_ordinary_sunday_item():
    assert is_main_sunday_sermon("Grace | Romans | Pastor Josh", _SUNDAY) is True


def test_is_main_sunday_sermon_false_for_non_sunday():
    assert is_main_sunday_sermon("Grace | Romans | Pastor Josh", _MONDAY) is False


def test_is_main_sunday_sermon_excludes_bonus_podcast_even_on_sunday():
    assert is_main_sunday_sermon("Grace || Bonus Podcast with Pastor Josh", _SUNDAY) is False


def test_is_main_sunday_sermon_excludes_church_at_home_even_on_sunday():
    assert is_main_sunday_sermon("Grace | Church At Home | Pastor Josh", _SUNDAY) is False


def test_is_main_sunday_sermon_excludes_bonus_qanda_even_on_sunday():
    assert is_main_sunday_sermon("Grace | Bonus Q&A | Pastor Josh", _SUNDAY) is False
