"""The admin strings exist in German, French and Italian, and the compiled .mo files are current."""

import re
from pathlib import Path

import polib
import pytest
from django.utils import translation

from djangocms_supertext.client import SupertextError
from djangocms_supertext.translator import localized

PACKAGE = Path(__file__).resolve().parent.parent / "djangocms_supertext"
LANGUAGES = ["de", "fr", "it"]
PLACEHOLDER = re.compile(r"%\(\w+\)s|<[^>]+>")


def source_strings() -> set[str]:
    """Every msgid marked in the code and templates (what makemessages would extract)."""
    found = set()
    for path in PACKAGE.rglob("*.py"):
        if "migrations" in path.parts:
            continue
        text = path.read_text()
        for match in re.finditer(r"\b(?:_|gettext_lazy|gettext_noop)\(\s*((?:\"[^\"]*\"\s*)+)", text):
            found.add("".join(re.findall(r"\"([^\"]*)\"", match.group(1))))
    for path in (PACKAGE / "templates").rglob("*.html"):
        text = path.read_text()
        found.update(re.findall(r"{% translate [\"']([^\"']+)[\"'] %}", text))
        found.update(re.findall(r"{{ _\(\"([^\"]+)\"\)", text))
        for body in re.findall(r"{% blocktranslate[^%]*%}(.*?){% endblocktranslate %}", text, re.S):
            found.add(re.sub(r"{{ (\w+) }}", r"%(\1)s", " ".join(body.split())))
    found.discard("Home")  # Django admin's own string
    return found


def test_source_strings_are_found():
    assert {"Translate with Supertext", "Translating…", "Translated with Supertext on %(date)s", "Supertext answered with HTTP %(code)s."} <= source_strings()


@pytest.mark.parametrize("language", LANGUAGES)
def test_catalog_is_complete(language):
    po = polib.pofile(str(PACKAGE / "locale" / language / "LC_MESSAGES" / "django.po"))
    assert source_strings() - {entry.msgid for entry in po} == set()
    for entry in po:
        assert entry.msgstr, entry.msgid
        assert "fuzzy" not in entry.flags, entry.msgid
        assert sorted(PLACEHOLDER.findall(entry.msgid)) == sorted(PLACEHOLDER.findall(entry.msgstr)), entry.msgid
        assert "Supertext" in entry.msgstr or "Supertext" not in entry.msgid, entry.msgid


@pytest.mark.parametrize("language", LANGUAGES)
def test_mo_matches_po(language):
    folder = PACKAGE / "locale" / language / "LC_MESSAGES"
    compiled = polib.mofile(str(folder / "django.mo"))
    assert {e.msgid: e.msgstr for e in compiled if e.msgid} == {e.msgid: e.msgstr for e in polib.pofile(str(folder / "django.po"))}


def test_errors_follow_the_admin_language():
    error = SupertextError("Supertext answered with HTTP %(code)s.", 418, params={"code": 418}, detail="teapot")
    assert str(error) == "Supertext answered with HTTP 418. (teapot)"
    with translation.override("fr"):
        assert localized(error) == "Supertext a répondu avec HTTP 418. (teapot)"
    with translation.override("it"):
        assert localized(error) == "Supertext ha risposto con HTTP 418. (teapot)"
