import logging
import time
from types import SimpleNamespace
from unittest import mock

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.core.signing import TimestampSigner
from django.template.loader import render_to_string
from django.test import RequestFactory
from mailing.exceptions import AllProvidersFailed, MailingUnavailable
from mailing.service import SendingStatus
from website import contact
from website.forms import make_ts

rf = RequestFactory()
PROXY = "10.0.0.1"


def _page(title="Work Field I", language="en"):
    return SimpleNamespace(title=title, language=language, get_public_path=lambda: "/en/work")


def _render_request():
    request = rf.get("/en")
    request.user = AnonymousUser()
    return request


def _old_ts(age=10):
    return TimestampSigner(salt="website.contact.ts").sign(str(int(time.time()) - age))


def _data(**overrides):
    data = {
        "firstname": "Ada",
        "lastname": "Lovelace",
        "email": "ada@example.org",
        "title": "Dr",
        "message": "Hello there",
        "website_url": "",
        "ts": _old_ts(),
    }
    data.update(overrides)
    return data


def _post(data=None, ip="1.2.3.4"):
    return rf.post(
        "/en", data if data is not None else _data(), REMOTE_ADDR=PROXY, HTTP_X_FORWARDED_FOR=ip
    )


@pytest.fixture(autouse=True)
def _local_cache(settings):
    """Always use an isolated in-memory cache (never the shared Redis, whatever settings module is active)."""
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "website-contact-tests",
        }
    }
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def send():
    with (
        mock.patch("website.contact.sending_status", return_value=SendingStatus(True, ())),
        mock.patch("website.contact.send_contact_message") as send_mock,
    ):
        yield send_mock


def _errors(form):
    return " ".join(form.non_field_errors())


def test_get_returns_unbound_form_and_flag(send):
    form, response, enabled = contact.handle_contact(rf.get("/en"), _page())
    assert response is None
    assert enabled is True
    assert not form.is_bound
    send.assert_not_called()


def test_valid_submission_sends_once_and_redirects(send):
    form, response, enabled = contact.handle_contact(_post(), _page())
    assert enabled is True
    assert response.status_code == 302
    assert response["Location"] == "/en/work?sent=1#contact-section"
    send.assert_called_once()
    kwargs = send.call_args.kwargs
    assert kwargs["reply_to"] == "ada@example.org"
    assert kwargs["subject"] == "Work Field I"
    assert "Lovelace" in kwargs["body"]
    assert "Hello there" in kwargs["body"]
    assert "Dr." in kwargs["body"]


def test_subject_has_crlf_removed_and_is_cut_to_200(send):
    contact.handle_contact(_post(), _page(title="Line\r\nBreak"))
    assert send.call_args.kwargs["subject"] == "LineBreak"
    cache.clear()
    contact.handle_contact(_post(), _page(title="x" * 250))
    assert send.call_args.kwargs["subject"] == "x" * 200


def test_lock_released_after_success(send):
    contact.handle_contact(_post(), _page())
    assert cache.get(contact.SENDING_LOCK_KEY) is None


def test_lock_released_after_exception(send):
    send.side_effect = RuntimeError("boom")
    with pytest.raises(RuntimeError):
        contact.handle_contact(_post(), _page())
    assert cache.get(contact.SENDING_LOCK_KEY) is None


def test_unavailable_post_rejected_and_button_disabled():
    with (
        mock.patch(
            "website.contact.sending_status", return_value=SendingStatus(False, ("no_provider",))
        ),
        mock.patch("website.contact.send_contact_message") as send_mock,
    ):
        form, response, enabled = contact.handle_contact(_post(), _page())
    assert response is None
    assert enabled is False
    assert "unavailable" in _errors(form)
    send_mock.assert_not_called()
    html = render_to_string(
        "website/partials/contact_section.html",
        {
            "contact_form": form,
            "contact_enabled": enabled,
            "contact_sent": False,
            "contact_form_id": "contact-form",
            "S": form.strings,
            "page": _page(),
        },
        request=_render_request(),
    )
    assert 'aria-disabled="true"' in html
    assert "disabled" in html.split("<button", 1)[1]
    assert form.strings["contact_unavailable"] in html


def test_enabled_button_has_no_disabled_attribute(send):
    form, _, enabled = contact.handle_contact(rf.get("/en"), _page())
    html = render_to_string(
        "website/partials/contact_section.html",
        {
            "contact_form": form,
            "contact_enabled": enabled,
            "contact_sent": True,
            "contact_form_id": "contact-form-wf2",
            "S": form.strings,
            "page": _page(),
        },
        request=_render_request(),
    )
    button = html.split("<button", 1)[1].split("</button>", 1)[0]
    assert "disabled" not in button
    assert 'id="contact-form-wf2"' in html
    assert form.strings["contact_success"] in html
    assert 'name="website_url"' in html
    assert 'aria-hidden="true"' in html
    assert 'tabindex="-1"' in html
    assert "csrfmiddlewaretoken" in html


def test_honeypot_redirects_without_sending(send):
    form, response, _ = contact.handle_contact(
        _post(_data(website_url="http://spam.example")), _page()
    )
    assert response.status_code == 302
    assert response["Location"] == "/en/work?sent=1#contact-section"
    send.assert_not_called()


def test_too_fast_submission_is_rejected(send):
    form, response, _ = contact.handle_contact(_post(_data(ts=make_ts())), _page())
    assert response is None
    assert form.strings["contact_too_fast"] in _errors(form)
    send.assert_not_called()


def test_tampered_ts_is_rejected(send):
    form, response, _ = contact.handle_contact(_post(_data(ts=_old_ts() + "x")), _page())
    assert response is None
    assert form.strings["contact_token_invalid"] in _errors(form)
    send.assert_not_called()


def test_ts_signed_with_other_salt_is_rejected(send):
    forged = TimestampSigner(salt="other").sign(str(int(time.time()) - 10))
    form, response, _ = contact.handle_contact(_post(_data(ts=forged)), _page())
    assert response is None
    assert form.strings["contact_token_invalid"] in _errors(form)
    send.assert_not_called()


def test_missing_ts_is_rejected(send):
    form, response, _ = contact.handle_contact(_post(_data(ts="")), _page())
    assert response is None
    send.assert_not_called()


def test_expired_ts_is_rejected(send):
    ts = _old_ts()
    with mock.patch("django.core.signing.time.time", return_value=time.time() + 25 * 3600):
        form, response, _ = contact.handle_contact(_post(_data(ts=ts)), _page())
    assert response is None
    assert form.strings["contact_token_invalid"] in _errors(form)
    send.assert_not_called()


@pytest.mark.parametrize(
    "overrides",
    [
        {"firstname": ""},
        {"email": "not-an-email"},
        {"title": "King"},
        {"message": "x" * 5001},
        {"firstname": "Ada\r\nBcc: evil@example.org"},
        {"lastname": "Love\nlace"},
    ],
)
def test_invalid_input_is_rejected(send, overrides):
    form, response, _ = contact.handle_contact(_post(_data(**overrides)), _page())
    assert response is None
    assert form.errors
    send.assert_not_called()


def test_message_of_5000_chars_is_accepted(send):
    _, response, _ = contact.handle_contact(_post(_data(message="x" * 5000)), _page())
    assert response is not None
    send.assert_called_once()


def test_per_ip_limit_sixth_submission_rejected(send):
    for _ in range(5):
        _, response, _ = contact.handle_contact(_post(), _page())
        assert response is not None
    form, response, _ = contact.handle_contact(_post(), _page())
    assert response is None
    assert form.strings["contact_rate_limited"] in _errors(form)
    assert send.call_count == 5


def test_subnet_limit_21st_submission_rejected(send, settings):
    settings.WEBSITE_TRUSTED_PROXY_HOPS = 1
    for i in range(20):
        _, response, _ = contact.handle_contact(_post(ip=f"1.2.3.{i + 1}"), _page())
        assert response is not None
    form, response, _ = contact.handle_contact(_post(ip="1.2.3.99"), _page())
    assert response is None
    assert form.strings["contact_rate_limited"] in _errors(form)
    assert send.call_count == 20


def test_global_limit(send, settings):
    settings.WEBSITE_CONTACT_GLOBAL_LIMIT_PER_HOUR = 3
    for i in range(3):
        _, response, _ = contact.handle_contact(_post(ip=f"1.{i}.3.4"), _page())
        assert response is not None
    form, response, _ = contact.handle_contact(_post(ip="1.99.3.4"), _page())
    assert response is None
    assert form.strings["contact_rate_limited"] in _errors(form)
    assert send.call_count == 3


def test_many_honeypot_submissions_do_not_block_genuine_one(send):
    for _ in range(600):
        _, response, _ = contact.handle_contact(_post(_data(website_url="spam")), _page())
        assert response is not None
    _, response, _ = contact.handle_contact(_post(), _page())
    assert response is not None
    send.assert_called_once()


def test_rejected_cap_logs_warning_once_then_goes_silent(send, settings, caplog):
    settings.WEBSITE_CONTACT_REJECTED_LIMIT_PER_HOUR = 3
    with caplog.at_level(logging.INFO, logger="website.contact"):
        for _ in range(10):
            contact.handle_contact(_post(_data(website_url="spam")), _page())
    infos = [r for r in caplog.records if r.levelno == logging.INFO]
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(infos) == 3
    assert len(warnings) == 1


def test_lock_held_gives_busy_error_and_keeps_quota(send):
    cache.add(contact.SENDING_LOCK_KEY, 1, 45)
    form, response, _ = contact.handle_contact(_post(), _page())
    assert response is None
    assert form.strings["contact_busy"] in _errors(form)
    send.assert_not_called()
    # lock owned by someone else must not be deleted by us
    assert cache.get(contact.SENDING_LOCK_KEY) == 1
    cache.delete(contact.SENDING_LOCK_KEY)
    for _ in range(5):
        _, response, _ = contact.handle_contact(_post(), _page())
        assert response is not None


def test_all_providers_failed_shows_friendly_error_and_logs_no_pii(send, caplog):
    send.side_effect = AllProvidersFailed(2)
    with caplog.at_level(logging.DEBUG):
        form, response, enabled = contact.handle_contact(_post(), _page())
    assert response is None
    assert enabled is True
    assert form.strings["contact_failed"] in _errors(form)
    assert cache.get(contact.SENDING_LOCK_KEY) is None
    logged = " ".join(r.getMessage() for r in caplog.records)
    for secret in ("ada@example.org", "Ada", "Lovelace", "Hello there", "1.2.3.4"):
        assert secret not in logged


def test_mailing_unavailable_during_send_shows_error(send):
    send.side_effect = MailingUnavailable(("no_key",))
    form, response, enabled = contact.handle_contact(_post(), _page())
    assert response is None
    assert enabled is False
    assert form.strings["contact_unavailable"] in _errors(form)
    assert cache.get(contact.SENDING_LOCK_KEY) is None


def test_no_pii_or_raw_ip_in_cache_keys_or_logs_on_rejection(send, caplog):
    with caplog.at_level(logging.DEBUG):
        contact.handle_contact(_post(_data(website_url="spam")), _page())
        contact.handle_contact(_post(), _page())
    keys = " ".join(str(k) for k in cache._cache)
    logged = " ".join(r.getMessage() for r in caplog.records)
    for text in (keys, logged):
        assert "1.2.3.4" not in text
        assert "ada@example.org" not in text


def test_german_page_uses_german_strings(send):
    form, _, _ = contact.handle_contact(rf.get("/de"), _page(language="de"))
    assert form.title_label("Herr") == "Herr"
    assert form.strings["contact_submit"] == "Kontakt aufnehmen"
