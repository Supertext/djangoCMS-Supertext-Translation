"""End to end on SQLite: a django CMS page with Text plugins is translated through a fake Supertext API."""

import pytest
from cms.api import add_plugin, create_page
from cms.models import PageContent
from django.contrib.auth.models import Permission, User
from django.urls import reverse

from djangocms_supertext import conf, translator
from djangocms_supertext.models import Translation
from tests.fake import FakeSession

pytestmark = pytest.mark.django_db

BODY = '<h2>From Bern</h2><p>Made by hand in <strong>Bern</strong>. See <a href="https://www.supertext.com">our website</a>.</p>'


@pytest.fixture
def page():
    page = create_page("Swiss chocolate", "page.html", "en", meta_description="Handmade pralines.", menu_title="Chocolate")
    placeholders = page.get_admin_content("en").rescan_placeholders()
    add_plugin(placeholders["content"], "TextPlugin", "en", body=BODY)
    add_plugin(placeholders["sidebar"], "TextPlugin", "en", body="<p>Opening hours</p>")
    return page


@pytest.fixture
def session(monkeypatch):
    session = FakeSession()
    monkeypatch.setattr("djangocms_supertext.client.requests.Session", lambda: session)
    return session


def options():
    return conf.load({"API_KEY": "test-key", "API_URL": "https://api.test/v1/", "LANGUAGES": {"de-ch": {"politeness": "more"}}, "POLL_INTERVAL": 0})


def texts(page, language):
    from djangocms_text.models import Text

    content = PageContent.admin_manager.get(page=page, language=language)
    bodies = {}
    for placeholder in content.get_placeholders():
        bodies[placeholder.slot] = [t.body for t in Text.objects.filter(placeholder=placeholder, language=language).order_by("position")]
    return content, bodies


def test_creates_translations_with_markup_and_plugins(page, session):
    client = options().client(session=session, sleep=lambda s: None)
    results = translator.translate_page(page, "en", ["de-ch", "fr-ch"], options=options(), client=client)

    assert [(r.language, r.status, r.created) for r in results] == [("de-ch", "translated", True), ("fr-ch", "translated", True)]
    content, bodies = texts(page, "de-ch")
    assert content.title == "[de-CH] Swiss chocolate"
    assert content.menu_title == "[de-CH] Chocolate"
    assert content.meta_description == "[de-CH] Handmade pralines."
    assert page.get_slug("de-ch") == "de-ch-swiss-chocolate"
    assert content.template == "page.html"
    assert bodies["content"] == ['<h2>[de-CH] From Bern</h2><p>[de-CH] Made by hand in <strong>[de-CH] Bern</strong>[de-CH] . See <a href="https://www.supertext.com">[de-CH] our website</a>[de-CH] .</p>']
    assert bodies["sidebar"] == ["<p>[de-CH] Opening hours</p>"]
    # The source is untouched
    assert texts(page, "en")[1]["content"] == [BODY]
    # One request per language, with tone and the primary source subtag
    posts = [c for c in session.calls if c["method"] == "POST"]
    assert [p["data"] for p in posts] == [
        {"target_lang": "de-CH", "source_lang": "en", "politeness": "more"},
        {"target_lang": "fr-CH", "source_lang": "en"},
    ]
    assert Translation.objects.filter(page=page, status="translated").count() == 2


def test_skips_existing_languages_unless_overwrite(page, session):
    client = options().client(session=session, sleep=lambda s: None)
    translator.translate_page(page, "en", ["de-ch"], options=options(), client=client)
    content, _ = texts(page, "de-ch")
    content.title = "Edited by hand"
    content.save()

    results = translator.translate_page(page, "en", ["de-ch"], options=options(), client=client)
    assert results[0].status == "skipped"
    assert texts(page, "de-ch")[0].title == "Edited by hand"

    results = translator.translate_page(page, "en", ["de-ch"], overwrite=True, options=options(), client=client)
    assert results[0].status == "translated" and not results[0].created
    content, bodies = texts(page, "de-ch")
    assert content.title == "[de-CH] Swiss chocolate"
    assert len(bodies["content"]) == 1 and len(bodies["sidebar"]) == 1  # replaced, not duplicated


def test_errors_are_reported_per_language(page):
    session = FakeSession(fail_status=500)
    client = options().client(session=session, sleep=lambda s: None)
    results = translator.translate_page(page, "en", ["de-ch"], options=options(), client=client)
    assert results[0].status == "error" and "unavailable" in results[0].message
    assert not PageContent.admin_manager.filter(page=page, language="de-ch").exists()


def test_describe(page, session):
    client = options().client(session=session, sleep=lambda s: None)
    translator.translate_page(page, "en", ["de-ch"], options=options(), client=client)
    languages = {lang["code"]: lang for lang in translator.describe(page)}
    assert languages["en"]["exists"] and languages["de-ch"]["exists"] and not languages["fr-ch"]["exists"]
    assert languages["de-ch"]["last_translation"] is not None


def editor(perm=True):
    user = User.objects.create_user("editor", "editor@example.com", "pw-123456789", is_staff=True)
    codenames = ["view_page", "change_page", "add_pagecontent", "change_pagecontent", "view_pagecontent"]
    perms = list(Permission.objects.filter(content_type__app_label="cms", codename__in=codenames))
    perms += list(Permission.objects.filter(content_type__app_label="djangocms_text"))
    if perm:
        perms += list(Permission.objects.filter(codename="translate"))
    user.user_permissions.set(perms)
    return user


def test_translate_dialog(page, session, client):
    client.force_login(editor())
    url = reverse("admin:djangocms_supertext_translate", args=[page.pk])
    response = client.get(url + "?language=en")
    assert response.status_code == 200
    assert b"Deutsch (Schweiz)" in response.content and b'value="de-ch"' in response.content

    response = client.post(url, {"source": "en", "targets": ["de-ch"]})
    assert response.status_code == 200
    assert b"translation created" in response.content
    assert PageContent.admin_manager.filter(page=page, language="de-ch").exists()
    assert Translation.objects.get(target_language="de-ch").user.username == "editor"


def test_translate_dialog_needs_permission(page, client):
    client.force_login(editor(perm=False))
    response = client.get(reverse("admin:djangocms_supertext_translate", args=[page.pk]))
    assert response.status_code == 403


def test_settings_page(session, client):
    admin = User.objects.create_superuser("admin", "admin@example.com", "pw-123456789")
    client.force_login(admin)
    url = reverse("admin:djangocms_supertext_settings")
    response = client.get(url)
    assert response.status_code == 200 and b"https://api.test/v1/" in response.content and b"de-CH" in response.content
    response = client.post(url, follow=True)
    assert b"Connected. The API key works." in response.content
