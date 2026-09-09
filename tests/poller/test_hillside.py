from poller.sources.hillside import _description_lines, _split_title_speaker, is_main_sunday_sermon

_SUNDAY = 6


def test_description_lines_splits_on_paragraph_boundaries():
    html = "<p>A Parting Conversation</p><p>Part 3 of the John series</p>"
    assert _description_lines(html) == ["A Parting Conversation", "Part 3 of the John series"]


def test_description_lines_handles_br_and_div_boundaries_and_entities():
    html = "<div>Grace &amp; Truth<br>continued</div>"
    assert _description_lines(html) == ["Grace & Truth", "continued"]


def test_description_lines_empty_description_yields_no_lines():
    assert _description_lines("") == []


def test_split_title_speaker_extracts_trailing_speaker():
    assert _split_title_speaker("9.6.26 | Hebrews 13:7-17 | Keith Crosby") == "Keith Crosby"


def test_split_title_speaker_archive_format_yields_none():
    assert _split_title_speaker("A Parting Conversation") is None


def test_is_main_sunday_sermon_true_for_sunday():
    assert is_main_sunday_sermon(_SUNDAY) is True


def test_is_main_sunday_sermon_false_for_undated_item():
    assert is_main_sunday_sermon(-1) is False
