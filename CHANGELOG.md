# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/).

## Unreleased

### Added

- The settings page shows the installed plugin version, linked to its release notes on GitHub.

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
