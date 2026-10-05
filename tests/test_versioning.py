"""With djangocms-versioning: new languages are drafts; published languages are not overwritten."""

import pytest
from django.conf import settings

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.skipif("djangocms_versioning" not in settings.INSTALLED_APPS, reason="run with --ds=tests.settings_versioning"),
]


def test_new_language_is_a_draft_and_published_ones_are_protected():
    from cms.api import add_plugin, create_page
    from django.contrib.auth.models import User
    from djangocms_versioning.constants import DRAFT
    from djangocms_versioning.models import Version

    from djangocms_supertext import conf, translator
    from tests.fake import FakeSession

    user = User.objects.create_superuser("admin", "admin@example.com", "pw-123456789")
    page = create_page("Swiss chocolate", "page.html", "en", created_by=user)
    content = translator.page_content(page, "en")
    add_plugin(content.rescan_placeholders()["content"], "TextPlugin", "en", body="<p>Hello</p>")
    options = conf.load({"API_KEY": "test-key", "API_URL": "https://api.test/v1/", "POLL_INTERVAL": 0})
    client = options.client(session=FakeSession(), sleep=lambda s: None)

    results = translator.translate_page(page, "en", ["de-ch"], user=user, options=options, client=client)
    assert results[0].status == "translated", results[0].message
    german = translator.page_content(page, "de-ch")
    assert Version.objects.get_for_content(german).state == DRAFT
    assert german.title == "[de-CH] Swiss chocolate"

    Version.objects.get_for_content(german).publish(user)
    results = translator.translate_page(page, "en", ["de-ch"], overwrite=True, user=user, options=options, client=client)
    assert results[0].status == "error" and "published" in results[0].message
