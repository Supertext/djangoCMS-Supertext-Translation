"""Settings and language codes (conf.py)."""

from djangocms_supertext import conf


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


def test_supertext_language_codes():
    options = conf.load({"LANGUAGES": {"de": {"code": "de_ch"}}})
    # Target: regional code; bare codes get a default region.
    assert options.target_code("fr") == "fr-FR"
    assert options.target_code("en") == "en-US"
    assert options.target_code("fr_ch") == "fr-CH"
    assert options.target_code("pt-br") == "pt-BR"
    assert options.target_code("zh-hant") == "zh-Hant"
    assert options.target_code("es-419") == "es-419"
    assert options.target_code("en-us-x-twain") == "en-US"  # variants and extensions dropped
    assert options.target_code("de_DE_formal") == "de-DE"
    assert options.target_code("xx") == "xx"  # unknown: sent unchanged
    # The override wins (normalized).
    assert options.target_code("de") == "de-CH"
    # Source: bare language, from the override if there is one.
    assert options.source_code("en") == "en"
    assert options.source_code("en-gb") == "en"
    assert options.source_code("de") == "de"
