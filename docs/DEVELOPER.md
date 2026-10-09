# Developer guide — Supertext Translation for django CMS

How the package is built, how to work on it, and how it is released and deployed.

## Architecture

A Django app (`djangocms_supertext`, package `djangocms-supertext-translation`) for django CMS 4.1+ (page contents per language, placeholders per page content).

```
Toolbar (edit mode): Language → "Translate with Supertext…"        cms_toolbars.py
   │ modal: GET/POST /admin/djangocms_supertext/translation/page/<page_id>/     admin.py (translate_view)
   │ needs djangocms_supertext.translate and permission to change the page
   ▼
translator.translate_page(page, source, targets, overwrite, user)
   │ _collect(): PageContent fields + configured plugin fields of the source's placeholders
   │ per target: skip if it exists (unless overwrite); with djangocms-versioning only drafts
   │ document.build(): one <div data-st-id="N"> per value; chunks below 900k characters
   ▼
client.SupertextClient   POST file → poll status → GET translation → DELETE   (requests)
   ▼
_apply(): create_page_content() (new language) or update the fields; replace the target's plugins with
          copies of the source's (copy_plugins_to_placeholder), set the translated fields (inline plugin
          ids in text bodies remapped); Translation rows as the log
```

| Module | Responsibility |
| --- | --- |
| `client.py` | Supertext AI file translation API v1 with `requests`. No Django imports; session and `sleep` injectable for tests |
| `document.py` | Builds/parses the HTML document (BeautifulSoup): HTML segments as is, plain text escaped with `<br>` for line breaks; chunking |
| `conf.py` | `SUPERTEXT` setting + `SUPERTEXT_API_KEY` / `SUPERTEXT_API_URL`; language code → Supertext code (`de-ch` → `de-CH`) and tone; `DEFAULT_PLUGIN_FIELDS` |
| `translator.py` | Field rules, translation, creating/replacing the target language |
| `models.py` | `Translation` (log; custom permission `translate`) |
| `admin.py` | Log list, translate dialog, settings page with *Test connection* and the plugin version (read from `djangocms_supertext.__version__`; X.Y.Z links to the GitHub release `vX.Y.Z`) (all as admin views, no URL include needed) |
| `cms_toolbars.py` | The toolbar entry |
| `management/commands/` | `supertext_translate <page id> --from en [--to de-ch fr-ch] [--overwrite]`, `supertext_check` |
| `locale/{de,fr,it}/` | German, French and Italian strings (`django.po` and compiled `django.mo`) |

### Field rules

- **Page content** (`PAGE_FIELDS`): `title`, `page_title`, `menu_title`, `meta_description`, as plain text.
- **Slug**: a new language gets django CMS's default slug from the translated title (`create_page_content(slug=None)`), unique within its parent. Existing languages keep their slug.
- **New language settings** (`COPIED_PAGE_SETTINGS`): `template`, `in_navigation`, `soft_root`, `limit_visibility_in_menu`, `xframe_options` come from the source.
- **Plugins**: every plugin of the source's placeholders is copied (`copy_plugins_to_placeholder`, so nested plugins and `copy_relations` work). Fields listed in `PLUGIN_FIELDS` for the plugin type are translated (`"html"` as HTML, `"text"` escaped). Defaults: `TextPlugin.body` (html), `LinkPlugin.name`, `PicturePlugin.caption_text`, `FilePlugin.file_name`, `VideoPlayerPlugin.label`.
- **Inline plugins** in text bodies (`<cms-plugin id="…">`) are remapped to the copies' ids after copying; their own texts (e.g. a link's name) are translated as plugins.
- **Overwrite** replaces the target's page fields and deletes the target's top-level plugins in each placeholder that the source has, then copies the source's.
- Empty values are skipped; an empty translation never overwrites.

Each value is one `data-st-id` element, so a whole Text plugin (all its paragraphs, bold words and links) is translated in context.

**djangocms-versioning:** `create_page_content` creates the new language as a draft version. Existing languages are only changed if their latest version is a draft (`_check_editable`).

## Supertext API protocol

Shared with the WordPress plugin and every other Supertext CMS plugin:

1. `POST {base}translate/ai/file`: multipart with `file` (part `Content-Type` exactly `text/html`, no charset, or the API answers 415), `target_lang` (BCP-47, e.g. `de-CH`), optional `source_lang` (primary subtag only, e.g. `en`, or the pair is rejected), optional `politeness` (`more`/`less`). Returns `{file_id}`.
2. `GET …/{file_id}/status` until `done` (`error`, `limit_exceeded`, `deleted` are terminal).
3. `GET …/{file_id}/translation` returns the translated HTML.
4. `DELETE …/{file_id}` (files also expire after 24 h).

Auth header: `Authorization: Supertext-Auth-Key <key>`. The header name must be `Authorization` (`Authentication` gets 403). Supertext shows the key with the prefix, so the client strips a pasted `Supertext-Auth-Key ` and always sends exactly one. Base URLs: `https://api.supertext.com/v1/` (live), `https://api.staging.supertext.com/v1/`, `https://api.testing.supertext.com/v1/`. `GET features` is the cost-free key check (*Test connection*, `supertext_check`).

**Rate limit:** the API limits requests per second per key (HTTP 429). The client retries a 429 up to 4 times, waiting for `Retry-After` if sent, otherwise 1, 2, 4 and 8 seconds plus jitter. Languages are translated one after the other.

## Local development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[test]" -r demo/requirements.txt
cd demo
python manage.py migrate
DEMO_ADMIN_EMAIL=you@example.com DEMO_ADMIN_PASSWORD='choose-one-1' python manage.py demo_setup
SUPERTEXT_API_KEY=… DJANGO_DEBUG=1 python manage.py runserver
# site: http://localhost:8000/en/   admin: http://localhost:8000/en/admin/
```

Without `DATABASE_URL` the demo uses SQLite (`demo/db.sqlite3`). To work without a real key, run the stand-in API (`node tests/docs/stand-in.mjs`) and start Django with `SUPERTEXT_API_KEY=anything SUPERTEXT_API_URL=http://127.0.0.1:8765/v1/`. It returns real German, French and Italian for the demo's pages and `[de-CH] …`-prefixed text for anything else.

## Tests

```bash
pytest
```

- `tests/test_client.py`: the API protocol, auth header and prefix, 429 retries, errors, clean-up.
- `tests/test_document.py`: HTML packing and parsing, line breaks, chunking, settings and language codes.
- `tests/test_translator.py`: end to end on SQLite with a fake API: a page with Text plugins in two placeholders is translated into two languages (fields, slug, markup, tone, plugins in the right placeholders, source untouched), skip and overwrite (no duplicated plugins), per-language errors, the translate dialog as an editor (and 403 without the permission), the settings page (including the plugin version and its release link) and *Test connection*.
- `tests/test_versioning.py` (`pytest --ds=tests.settings_versioning tests/test_versioning.py`, needs djangocms-versioning): new languages are drafts, published languages are not overwritten.

CI (`.github/workflows/ci.yml`) on every push and pull request:

- **test**: the suite on Python 3.11 with django CMS 4.x and Django 4.2, 3.12 with django CMS 5.0 and Django 5.2, 3.13 with django CMS 5.1 and Django 6 (plus the versioning test).
- **demo**: builds the demo image, starts it twice against PostgreSQL with the stand-in (`tests/demo-check.sh`): demo accounts created once and never duplicated, no passwords in the log, the editor's permissions, `supertext_check`, translation of the sample page into three languages, the skip on a second run, and the German and French pages with their translated slugs and markup.

## Demo (Railway)

The public demo is a container built from `demo/Dockerfile`: django CMS 5.1 with djangocms-text and this package, English plus German, French and Italian (Switzerland), a home page and a sample article. It runs on Railway in the `supertext-cms-demos` project, service `djangoCMS`, region EU West (Amsterdam): <https://djangocms-production.up.railway.app/en/> (admin: `/en/admin/`). The data lives in a `djangocms` database on the project's PostgreSQL service.

**Deploys:** Railway builds `main` of this repository (`railway.json` points it at `demo/Dockerfile`).

**What's in `demo/`:**

| File | Purpose |
| --- | --- |
| `Dockerfile` | `python:3.13-slim`, the demo's requirements and this package (installed from the repository), `collectstatic` |
| `entrypoint.sh` | Every start: creates the database if missing, `migrate`, `demo_setup`, then gunicorn on `$PORT` |
| `demo/settings.py` | Settings from environment variables; PostgreSQL via `DATABASE_URL` (database name `DJANGOCMS_DB_NAME`); WhiteNoise; `CMS_PERMISSION = False`; Supertext with formal tone for the three target languages |
| `site_setup/` | The page template (`page.html` with a language chooser) and the `demo_setup` command |
| `createdb.py` | Creates the demo database on the server from `DATABASE_URL` |
| `.env.example` | The variables below |

**No volume:** Railway's volume limit for the project is reached, and the demo needs none: everything is in PostgreSQL. Uploaded media would disappear with the next deploy.

**Service variables:**

| Variable | |
| --- | --- |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}`; the demo database (`DJANGOCMS_DB_NAME`, default `djangocms`) is created on that server if missing |
| `DJANGO_SECRET_KEY` | Random secret |
| `DEMO_ADMIN_EMAIL`, `DEMO_ADMIN_PASSWORD` | Superuser (the e-mail address is also the username) |
| `DEMO_EDITOR_EMAIL`, `DEMO_EDITOR_PASSWORD` | Editor for automated tests and screenshots: staff user in the **Editors** group (pages, page contents, text plugins, *Can translate pages with Supertext*). django CMS has no built-in editor role, so `demo_setup` creates this group. |
| `SUPERTEXT_API_KEY` | Supertext key |
| `SUPERTEXT_API_URL` | Optional, e.g. a stand-in API |
| `PORT` | Port gunicorn listens on (Railway sets it) |

Railway also sets `RAILWAY_PUBLIC_DOMAIN`, which the settings use for `CSRF_TRUSTED_ORIGINS` and `demo_setup` for the Django site's domain.

**Demo accounts:** on every start `demo_setup` creates the `DEMO_ADMIN` and `DEMO_EDITOR` accounts if no account with that e-mail address or username exists. Existing accounts are never changed; change passwords in the admin. Passwords must pass Django's password validators (at least 8 characters, not too common, not only digits, not too similar to the e-mail address); if one doesn't, that account is skipped with a warning naming the variable and the rule, and the demo still starts. django CMS has no first-run "create admin" screen; without `DEMO_ADMIN_*` there is simply no superuser.

**Run it locally:**

```bash
docker build -f demo/Dockerfile -t supertext-djangocms-demo .
docker run --rm -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host.docker.internal:5432/postgres -e DJANGO_SECRET_KEY=dev \
  -e DEMO_ADMIN_EMAIL=you@example.com -e DEMO_ADMIN_PASSWORD='choose-one-1' \
  -e SUPERTEXT_API_KEY=… supertext-djangocms-demo
```

## Docs screenshots

The images in `docs/images/` are generated by `tests/docs/screenshots.mjs` (Playwright) from a freshly set-up demo whose package talks to `tests/docs/stand-in.mjs`. The stand-in returns German, French and Italian for the demo's pages (`samples.json`, real Supertext output). Regenerate them whenever a screen they show changes:

```bash
cd tests/docs && npm install && npx playwright install chromium
npm run stand-in &
# a fresh demo database (migrate + demo_setup with DEMO_* set), served on :8095 with
# SUPERTEXT_API_KEY=anything SUPERTEXT_API_URL=http://127.0.0.1:8765/v1/
BASE_URL=http://127.0.0.1:8095 DEMO_ADMIN_EMAIL=… DEMO_ADMIN_PASSWORD=… \
  DEMO_EDITOR_EMAIL=… DEMO_EDITOR_PASSWORD=… npm run screenshots
```

On the settings page the script shows the live API address and the public demo's domain (`SITE_DOMAIN`) instead of the local ones.

## Code quality and security checks

- **Checks** workflow (`.github/workflows/checks.yml`): [actionlint](https://github.com/rhysd/actionlint) and [zizmor](https://docs.zizmor.sh/) lint the workflows on every push and pull request. Dependency review fails a pull request that adds a package with a known vulnerability (moderate or worse). Actions are pinned to commit SHAs; Dependabot keeps the pins up to date. To run the workflow lint locally: `pip install actionlint-py zizmor`, then `actionlint` and `zizmor .github/workflows` in the repo root.
- **Links** workflow (`.github/workflows/links.yml`): [lychee](https://lychee.cli.rs/) checks the links in all Markdown files weekly and whenever docs change on `main`. Broken links open (or update) the issue "Broken links in the docs". Links that can't work from CI (local URLs, placeholders, pages behind a login) are excluded in `.lycheeignore`.
- Python and the demo's JavaScript are analysed by CodeQL (see below), so this repo runs no separate static analyser.
- GitHub settings (set by Remy's setup script, not stored in the repo): **secret scanning with push protection** (a push containing a known token format is rejected; findings under *Security → Secret scanning*) and **CodeQL default setup** (findings under *Security → Code scanning* and as comments on pull requests; PHP isn't covered by CodeQL, which is why the PHP plugins run PHPStan).

Before starting work in this repo, look at its open findings: code scanning alerts, secret scanning alerts, Dependabot PRs and the "Broken links in the docs" issue.

## Releasing

Releases are published by `.github/workflows/release.yml` when the version is officially bumped; nobody tags or creates releases by hand.

1. Check that if messages changed, each `.mo` is recompiled (`python -c "import polib; polib.pofile('djangocms_supertext/locale/de/LC_MESSAGES/django.po').save_as_mofile('djangocms_supertext/locale/de/LC_MESSAGES/django.mo')"`, same for `fr` and `it`; `tests/test_locale.py` fails otherwise).
2. Move the *Unreleased* entries in `CHANGELOG.md` under a new `## X.Y.Z — YYYY-MM-DD` section, and keep an empty *Unreleased* above it.
3. Set the same version in:
   - `djangocms_supertext/__init__.py`: `__version__`, the Python package version
4. Push to `main`. The workflow checks that the version files match `CHANGELOG.md`, then tags `vX.Y.Z` and creates the GitHub release with the CHANGELOG section as notes (0.x versions as pre-releases). A push that adds no new version does nothing, and a version that is already released is skipped. After fixing a failed run, start it again with *Run workflow* on the *Release* workflow.

Publishing to PyPI (`python -m build && twine upload dist/*`) is planned.
## Conventions

- Black-compatible formatting, type hints in new code.
- User-visible strings via Django's gettext, translated in `djangocms_supertext/locale/{de,fr,it}/LC_MESSAGES/django.po` (English is the source). New or changed strings need all four languages in the same commit. `client.py` has no Django imports, so it marks its error messages with a local `gettext_noop` and keeps `template`/`params` on `SupertextError`; `translator.localized()` translates them for the dialog, the settings page and the log. `tests/test_locale.py` checks that every marked string is in each catalog, placeholders match and the `.mo` files are current.
- Keep `client.py` and `document.py` free of Django imports.
- Keep the three docs in `docs/` current with every change (see `CLAUDE.md`).

## Known limitations / roadmap

- Translation runs inside the editor's request (one language after the other, up to `TIMEOUT` each). Planned: background translation and translating a page tree in one go.
- Overwriting replaces all plugins of the target language with translated copies of the source's; plugins that exist only in the target language are removed in placeholders the source has.
- Existing languages keep their slug when overwritten.
- Static placeholders/aliases (djangocms-alias) and apphook content are not translated.
- With djangocms-versioning, only drafts can be overwritten.
- Not on PyPI yet.
- Human (professional) translation orders are not supported yet (the WordPress plugin has them).
