from poller.sources.pbc import (
    _split_title,
    episode_url_from_link,
    is_main_sunday_sermon,
    parse_sermons_page_speakers,
)

_SUNDAY = 6
_MONDAY = 0


def test_is_main_sunday_sermon_requires_main_service_segment_and_sunday():
    assert is_main_sunday_sermon("https://cdn.pbc.org/Main_Service/ep1.mp3", _SUNDAY) is True


def test_is_main_sunday_sermon_excludes_other_service_segments():
    assert is_main_sunday_sermon("https://cdn.pbc.org/Youth_Service/ep1.mp3", _SUNDAY) is False


def test_is_main_sunday_sermon_excludes_non_sunday_main_service():
    assert is_main_sunday_sermon("https://cdn.pbc.org/Main_Service/ep1.mp3", _MONDAY) is False


def test_split_title_separates_trailing_series():
    assert _split_title("Hear and Do - Luke") == ("Hear and Do", "Luke")


def test_split_title_with_no_series_suffix_keeps_whole_title():
    assert _split_title("Hear and Do") == ("Hear and Do", None)


def test_episode_url_from_link_rebuilds_against_sermons_page():
    raw = "https://pbc.org?enmse_mid=4687"
    assert episode_url_from_link(raw) == "https://pbc.org/sermons?enmse=1&enmse_am=1&enmse_mid=4687"


def test_episode_url_from_link_passes_through_when_no_mid():
    raw = "https://pbc.org/some-page"
    assert episode_url_from_link(raw) == raw


def test_parse_sermons_page_speakers_extracts_mid_to_speaker_mapping():
    html = b"""
    <div class="card">
      <h5>Hear and Do</h5>
      <p class="enmse-speaker-name">Jane Doe</p>
      <a href="?enmse_mid=4687">Watch</a>
    </div>
    """
    assert parse_sermons_page_speakers(html) == {"4687": "Jane Doe"}
