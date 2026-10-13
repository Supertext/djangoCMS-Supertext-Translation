import pytest

from djangocms_supertext.client import SDK_VERSION, Segment, SupertextClient, SupertextError, base_url_for, normalize_key
from tests.fake import FakeSession


def client(session, key="test-key"):
    return SupertextClient(key, "https://api.test/v1/", session=session, poll_interval=0, sleep=lambda s: None)


def test_full_protocol():
    session = FakeSession(statuses=["running", "done"])
    html = client(session).translate_document('<div data-st-id="0">Hello</div>', "de-CH", "en", "more")
    assert "[de-CH] Hello" in html
    assert [(c["method"], c["url"].split("/v1/")[1]) for c in session.calls] == [
        ("POST", "translate/ai/file"),
        ("GET", "translate/ai/file/f1/status"),
        ("GET", "translate/ai/file/f1/status"),
        ("GET", "translate/ai/file/f1/translation"),
        ("DELETE", "translate/ai/file/f1"),
    ]
    post = session.calls[0]
    assert post["data"] == {"target_lang": "de-CH", "source_lang": "en", "politeness": "more"}
    assert post["files"]["file"][2] == "text/html"
    assert post["headers"]["Authorization"] == "Supertext-Auth-Key test-key"


def test_accepts_key_with_prefix():
    session = FakeSession()
    client(session, "  Supertext-Auth-Key test-key ").validate_api_key()
    assert session.calls[0]["headers"]["Authorization"] == "Supertext-Auth-Key test-key"
    assert normalize_key("supertext-auth-key abc") == "abc"


def test_retries_rate_limit():
    session = FakeSession(rate_limited=2)
    client(session).validate_api_key()
    assert len(session.calls) == 3


def test_gives_up_after_four_retries():
    session = FakeSession(rate_limited=99)
    with pytest.raises(SupertextError, match="Too many requests"):
        client(session).validate_api_key()
    assert len(session.calls) == 5


def test_segments_in_one_document():
    session = FakeSession()
    out = client(session).translate_segments(
        [Segment("Hello <b>world</b>", html=True), Segment("Fish & chips\nto go"), Segment("  ")], "de-DE", "en"
    )
    assert out == {0: "[de-DE] Hello <b>[de-DE] world</b>", 1: "[de-DE] Fish & chips\n[de-DE] to go"}  # blank: not sent
    assert session.calls[0]["data"]["target_lang"] == "de-DE"  # sent as given
    assert sum(c["method"] == "POST" for c in session.calls) == 1


def test_invalid_language_pair_names_the_codes():
    with pytest.raises(SupertextError, match=r"does not support this language pair \(en → es-ES\)") as info:
        client(FakeSession()).translate_document("<p>x</p>", "es-ES", "en")
    assert info.value.code == "invalid_language_pair"
    assert info.value.params == {"source": "en", "target": "es-ES"}


def test_politeness_where_supertext_has_none_is_refused_before_sending():
    session = FakeSession()
    with pytest.raises(SupertextError, match=r"no formal or informal tone for this language \(en-US\)") as info:
        client(session).translate_document("<p>x</p>", "en-US", "de", "more")
    assert info.value.code == "unsupported_feature" and session.calls == []
    assert "[en-US]" in client(session).translate_document("<p>x</p>", "en-US", "de")  # default tone works


def test_key_check():
    assert client(FakeSession()).check_api_key().status == "ok"
    assert client(FakeSession(), "wrong").check_api_key().status == "invalid"
    assert client(FakeSession(), "").check_api_key().status == "missing"


def test_vendored_sdk_version():
    assert SDK_VERSION.count(".") == 2


def test_authentication_error():
    with pytest.raises(SupertextError, match="Authentication failed.*bad key"):
        client(FakeSession(), "wrong").translate_document("<p>x</p>", "fr-FR")


def test_limit_exceeded_cleans_up():
    session = FakeSession(statuses=["limit_exceeded"])
    with pytest.raises(SupertextError, match="limit is exceeded"):
        client(session).translate_document("<p>x</p>", "fr-FR")
    assert session.calls[-1]["method"] == "DELETE"


def test_missing_key():
    with pytest.raises(SupertextError, match="No Supertext API key"):
        client(FakeSession(), "").validate_api_key()


def test_environments():
    assert base_url_for("staging") == "https://api.staging.supertext.com/v1/"
    assert base_url_for("live", "http://127.0.0.1:8765/v1/") == "http://127.0.0.1:8765/v1/"
