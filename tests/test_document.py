from djangocms_supertext import conf
from djangocms_supertext.document import Segment, build, chunks, parse


def test_round_trip_keeps_markup_and_line_breaks():
    segments = [Segment("Fish & chips\nsecond line"), Segment("<p>Hello <b>world</b></p>", html=True)]
    document = build(segments)
    assert '<div data-st-id="0">Fish &amp; chips<br>second line</div>' in document
    assert parse(document, segments) == {0: "Fish & chips\nsecond line", 1: "<p>Hello <b>world</b></p>"}


def test_ignores_unknown_ids():
    assert parse('<div data-st-id="7">x</div><div data-st-id="a">y</div>', [Segment("a")]) == {}


def test_chunks():
    assert chunks([Segment("aaaaaa"), Segment("bbbbbb"), Segment("ccc")], 10) == [[0], [1, 2]]


def test_language_codes_and_settings(monkeypatch):
    monkeypatch.setenv("SUPERTEXT_API_KEY", "Supertext-Auth-Key env-key")
    monkeypatch.setenv("SUPERTEXT_API_URL", "http://127.0.0.1:8765/v1/")
    options = conf.load({"API_KEY": "settings-key", "LANGUAGES": {"fr": {"code": "fr-CH", "politeness": "less"}}, "PLUGIN_FIELDS": {"HeroPlugin": {"heading": "text"}}})
    assert options.api_key == "env-key" and options.api_key_source == "environment"
    assert options.base_url == "http://127.0.0.1:8765/v1/"
    assert options.target_code("de-ch") == "de-CH"
    assert options.target_code("fr") == "fr-CH" and options.politeness("fr") == "less"
    assert options.plugin_fields["HeroPlugin"] == {"heading": "text"}
    assert options.plugin_fields["TextPlugin"] == {"body": "html"}
