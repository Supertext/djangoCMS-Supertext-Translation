import pytest

from djangocms_supertext.client import SupertextClient, SupertextError, base_url_for, normalize_key, retry_delay
from tests.fake import FakeSession


def client(session, key="test-key"):
    return SupertextClient(key, "https://api.test/v1/", session=session, poll_interval=0, sleep=lambda s: None)


def test_full_protocol():
    session = FakeSession(statuses=["running", "done"])
    html = client(session).translate_document('<div data-st-id="0">Hello</div>', "de-CH", "en-GB", "more")
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


def test_retry_after():
    assert retry_delay(0, "3") == 3
    assert retry_delay(1) >= 2


def test_authentication_error():
    with pytest.raises(SupertextError, match="Authentication failed.*bad key"):
        client(FakeSession(), "wrong").translate_document("<p>x</p>", "fr")


def test_limit_exceeded_cleans_up():
    session = FakeSession(statuses=["limit_exceeded"])
    with pytest.raises(SupertextError, match="limit is exceeded"):
        client(session).translate_document("<p>x</p>", "fr")
    assert session.calls[-1]["method"] == "DELETE"


def test_missing_key():
    with pytest.raises(SupertextError, match="No Supertext API key"):
        client(FakeSession(), "").validate_api_key()


def test_environments():
    assert base_url_for("staging") == "https://api.staging.supertext.com/v1/"
    assert base_url_for("live", "http://127.0.0.1:8765/v1/") == "http://127.0.0.1:8765/v1/"
