from poller.sources.north_point import _split_title, is_main_sunday_sermon


def test_is_main_sunday_sermon_true_for_any_sunday_item():
    assert is_main_sunday_sermon(6) is True


def test_is_main_sunday_sermon_false_for_non_sunday():
    assert is_main_sunday_sermon(0) is False


def test_split_title_separates_trailing_speaker():
    assert _split_title("Better Together // Andy Stanley") == ("Better Together", "Andy Stanley")


def test_split_title_with_no_separator_keeps_whole_title():
    assert _split_title("Better Together") == ("Better Together", None)
