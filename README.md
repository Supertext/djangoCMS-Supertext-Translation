# Supertext Translation for django CMS

Translate django CMS pages into the site's other languages with **Supertext AI**, right from the toolbar.

In edit mode, choose **Language → Translate with Supertext…**, tick the languages and click **Translate**: the page's title, menu title, meta description and the texts of its plugins go to Supertext in one request per language and come back as a new language version of the page, with all plugins in place. Editors review and adjust it like any other page content.

- Uses django CMS's own languages and page contents; works with djangocms-versioning (new languages are drafts)
- Text plugins keep their headings, bold text, links and lists; whole paragraphs are translated in context
- Translated URL slugs for new languages
- Languages that exist are kept unless the editor explicitly overwrites them
- Text, Link, Picture, File and Video plugins out of the box; more plugin fields by setting
- Formal or informal tone and custom Supertext language codes per language
- A settings page with *Test connection*, a translation log, management commands

![The Translate with Supertext dialog in the django CMS toolbar](docs/images/02-translate-dialog.png)

## Documentation

| Guide | For |
| --- | --- |
| [Installation guide](docs/INSTALLATION.md) | Administrators and developers: requirements, install, API key, languages, permissions, settings, troubleshooting |
| [User guide](docs/USER_GUIDE.md) | Editors: translating, reviewing, overwriting, what gets translated |
| [Developer guide](docs/DEVELOPER.md) | Architecture, API protocol, local development, tests, demo deployment, releases |

Quick start:

```bash
pip install git+https://github.com/Supertext/djangoCMS-Supertext-Translation.git
```

```python
# settings.py
INSTALLED_APPS += ["djangocms_supertext"]
# environment: SUPERTEXT_API_KEY="…"
```

```bash
python manage.py migrate djangocms_supertext
```

## Demo

`demo/` is a django CMS 5 site with English sample pages and German, French and Italian (Switzerland), deployed to Railway from this repository. See the [developer guide](docs/DEVELOPER.md#demo-railway).

Part of Supertext's translation plugins for open source CMSs, alongside [Wagtail](https://github.com/Supertext/Wagtail-Supertext-Translation), [WordPress](https://github.com/Supertext/supertext-wordpress-polylang), [Drupal](https://www.drupal.org/project/tmgmt_supertext_ai) and others.

## Changelog and roadmap

See [CHANGELOG.md](CHANGELOG.md) and the [roadmap](docs/DEVELOPER.md#known-limitations--roadmap).

## License

MIT. © Supertext AG
