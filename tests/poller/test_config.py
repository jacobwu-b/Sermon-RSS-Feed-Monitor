import pytest

from poller import config


def test_load_churches_parses_a_valid_object():
    raw = '{"menlo": {"rss": "https://example.org/feed.xml", "enabled": true, "notify": false}}'
    churches = config.load_churches(raw)
    assert churches["menlo"] == config.ChurchConfig(
        name="menlo", rss="https://example.org/feed.xml", enabled=True, notify=False
    )


def test_load_churches_defaults_missing_flags_to_false():
    churches = config.load_churches('{"menlo": {"rss": "https://example.org/feed.xml"}}')
    assert churches["menlo"].enabled is False
    assert churches["menlo"].notify is False


def test_load_churches_rejects_empty_value():
    with pytest.raises(config.ConfigError):
        config.load_churches("")


def test_load_churches_rejects_invalid_json():
    with pytest.raises(config.ConfigError):
        config.load_churches("{not json")


def test_load_churches_rejects_non_object_top_level():
    with pytest.raises(config.ConfigError):
        config.load_churches("[]")


def test_load_churches_rejects_non_object_entry():
    with pytest.raises(config.ConfigError):
        config.load_churches('{"menlo": "not an object"}')


def test_load_notify_config_reads_all_three_secrets(monkeypatch):
    monkeypatch.setenv("NOTIFY_EMAIL_FROM", "alerts@example.org")
    monkeypatch.setenv("NOTIFY_EMAIL_TO", "team@example.org")
    monkeypatch.setenv("RESEND_API_KEY", "re_123")
    cfg = config.load_notify_config()
    assert cfg == config.NotifyConfig(
        from_addr="alerts@example.org", to_addr="team@example.org", api_key="re_123"
    )


def test_load_notify_config_raises_when_any_secret_missing(monkeypatch):
    monkeypatch.delenv("NOTIFY_EMAIL_FROM", raising=False)
    monkeypatch.setenv("NOTIFY_EMAIL_TO", "team@example.org")
    monkeypatch.setenv("RESEND_API_KEY", "re_123")
    with pytest.raises(config.ConfigError, match="NOTIFY_EMAIL_FROM"):
        config.load_notify_config()
