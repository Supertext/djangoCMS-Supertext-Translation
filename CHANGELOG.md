# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/).

## Unreleased

### Added

- Support for Python 3.14 (tested in CI with django CMS 5.1 and Django 6).
- Automatic API key check: when the key is new or changed, on *Test connection*, in `supertext_check` and when Supertext rejects the key during a translation. The settings page shows the latest result with its time (*the connection works*, *rejected*, *no key*, *Supertext can't be reached*, *error*), with links to create an account and generate a key, in English, German, French and Italian.
- *Send version information to Supertext* (on by default; `"VERSION_REPORTS": False` in `SUPERTEXT` or `SUPERTEXT_VERSION_REPORTS=0` turns it off): after an update and when the key check result changes, the package sends the site URL, the package, django CMS, Python and SDK versions, whether a key is set, the key check result and the ping address to Supertext. No content, no API key and no personal data. Shown on the settings page. New option `SITE_URL` for the site's public address.
- Public ping endpoint `<admin>/djangocms_supertext/translation/ping/` (optionally `/supertext/ping` with `include("djangocms_supertext.urls")`) that only echoes Supertext's challenge, so Supertext can check the site is reachable (404 with version reports off).
- New table for this state (migration `0002_state`): run `python manage.py migrate djangocms_supertext` after updating.
- Messages for a language without a Supertext language (*has no Supertext language yet*) and for a formal/informal tone Supertext doesn't offer for a language, in all four languages. The settings page marks unmapped languages (*Not mapped*), warns about such a tone and lists all Supertext languages.

- Its own message for an unsupported language pair, naming the codes ("Supertext does not support this language pair (en → xx-YY)"), in English, German, French and Italian.
- French and Italian interface (and German where it was missing): the dialog, settings page, log and all Supertext error messages follow the user's interface language.
- The settings page shows the installed plugin version, linked to its release notes on GitHub.

### Changed

- **Languages are no longer guessed.** A django CMS language code that is a Supertext code (`de-ch`, `fr-ch`, `es`, `zh-hans`, apart from case and `_`/`-`) is used as it is; every other code needs a `code` under `SUPERTEXT["LANGUAGES"]` (e.g. `"de": {"code": "de-CH"}`, `"en": {"code": "en-GB"}`). Default regions are gone: they were wrong for most languages (Supertext wants `es`, `sl`, `nl` without region, `zh-Hans` instead of `zh-CN`). An unmapped language is reported and nothing is sent for it. A formal/informal tone for a language without it is reported instead of being sent.
- *Test connection* shows the key check result (also for a rejected key) instead of *Connected. The API key works.*; `supertext_check` also sends a version report and prints the plugin version.
- All Supertext API calls now go through the official Supertext Python SDK (0.2.0, commit `c66cb4d`, `v1` namespace), shipped inside the package (nothing extra to install). The `beautifulsoup4` dependency is gone.

### Changed

- The "No Supertext API key" and "Authentication failed" messages from the API client now link to account signup and API key generation.

## 0.1.0 — 2026-10-07

### Added

- First version for django CMS 4.1 and later.
- *Translate with Supertext…* in the toolbar's Language menu: a dialog to translate the page from one language into others, with "Already translated" / "Translated with Supertext on …" per language and an explicit *Overwrite existing translations* option.
- Translates the page title, page title, menu title and meta description, and the texts of the page's plugins: Text (as HTML, markup kept), Link, Picture, File and Video plugins out of the box, more via `SUPERTEXT["PLUGIN_FIELDS"]`. Plugins are copied into the new language; inline plugins in text bodies are relinked.
- New languages get a slug from the translated title; with djangocms-versioning they are created as drafts, and published languages are not overwritten.
- Permission *Can translate pages with Supertext*; page change permissions apply.
- Admin: a log of all Supertext translations and a settings page with *Test connection* (superusers).
- The settings page, the "not set up yet" notice in the translate dialog and `supertext_check` link to the Supertext account signup and to supertext.com → Integrations → API, where users with the Admin role generate the API key. Installation guide and README explain the same.
- Settings: `SUPERTEXT_API_KEY` (with or without the `Supertext-Auth-Key` prefix), `SUPERTEXT_API_URL`, and the `SUPERTEXT` setting (environment, languages and tone, timeout, plugin fields).
- Management commands `supertext_translate` and `supertext_check`.
- Retries when the Supertext API answers HTTP 429 (rate limit).
- German admin strings.
- Demo for Railway (`demo/`) with demo accounts, an Editors group and English sample pages created on every start.
