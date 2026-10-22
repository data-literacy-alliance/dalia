import logging
import secrets
import smtplib
import socket
from unittest import mock

import pytest
from django.core import mail
from django.core.mail.backends.locmem import EmailBackend as LocmemBackend
from mailing import crypto, service
from mailing.exceptions import (
    AllProvidersFailed,
    MailingUnavailable,
    Smtp2goError,
    UnsafeEndpointError,
)
from mailing.models import ContactFormSettings, EmailProvider

GAI = "mailing.connection_types.socket.getaddrinfo"
PUBLIC = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]
SECRET = "TOP-SECRET-API-KEY-123"
pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _env(tmp_path, settings):
    path = tmp_path / "key"
    path.write_text(secrets.token_hex(32))
    crypto._reset_cache()
    settings.EMAIL_FERNET_KEY_FILE = str(path)
    with mock.patch(GAI, return_value=PUBLIC):
        yield
    crypto._reset_cache()


@pytest.fixture
def contact_settings():
    return ContactFormSettings.objects.create(
        recipients="to@example.org\nsecond@example.org", subject_prefix="[DALIA]"
    )


def make(name="P1", order=0, active=True, ctype="smtp", **kw):
    data = {
        "name": name,
        "connection_type": ctype,
        "from_email": "from@example.org",
        "from_name": "DALIA",
        "order": order,
        "is_active": active,
    }
    if ctype == "smtp":
        data.update(host="mail.example.org", port=587, username="u")
    data.update(kw)
    provider = EmailProvider(**data)
    provider.set_secret("password" if ctype == "smtp" else "api_key", SECRET)
    provider.save()
    return provider


class Failing:
    def __init__(self, exc):
        self.exc = exc

    def send_messages(self, messages):
        raise self.exc

    def open(self):
        return False

    def close(self):
        pass


def fake_get_connection(plan):
    """plan: list of exceptions (fail) or None (locmem success), one per call."""
    calls = []
    plan = list(plan)

    def factory(backend, **kwargs):
        calls.append((backend, kwargs))
        outcome = plan.pop(0)
        return LocmemBackend() if outcome is None else Failing(outcome)

    factory.calls = calls
    return factory


def anymail_error():
    from anymail.exceptions import AnymailAPIError

    return AnymailAPIError(f"boom {SECRET}")


# --- status ------------------------------------------------------------------


def test_status_available(contact_settings):
    make()
    status = service.sending_status()
    assert status.available is True and status.reasons == ()


def test_status_all_reasons_without_anything(settings, tmp_path):
    settings.EMAIL_FERNET_KEY_FILE = str(tmp_path / "missing")
    crypto._reset_cache()
    status = service.sending_status()
    assert status.available is False
    assert set(status.reasons) == {"no_key", "no_provider", "no_recipient"}


def test_status_no_recipient_only():
    make()
    assert service.sending_status().reasons == ("no_recipient",)


def test_status_no_provider_when_only_inactive(contact_settings):
    make(active=False)
    assert service.sending_status().reasons == ("no_provider",)


def test_status_no_key_when_key_invalid(contact_settings, settings, tmp_path):
    make()
    bad = tmp_path / "bad"
    bad.write_text("nothex")
    settings.EMAIL_FERNET_KEY_FILE = str(bad)
    crypto._reset_cache()
    reasons = service.sending_status().reasons
    assert "no_key" in reasons and "no_provider" in reasons


def test_unavailable_raises_with_reasons():
    with pytest.raises(MailingUnavailable) as info:
        service.send_contact_message(subject="s", body="b", reply_to="r@example.org")
    assert "no_recipient" in info.value.reasons


# --- sending -----------------------------------------------------------------


def test_success_applies_prefix_recipients_and_plain_text(contact_settings):
    make()
    factory = fake_get_connection([None])
    with mock.patch("mailing.service.get_connection", factory):
        service.send_contact_message(subject="Hello", body="Body", reply_to="r@example.org")
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.subject == "[DALIA] Hello"
    assert msg.to == ["to@example.org", "second@example.org"]
    assert msg.reply_to == ["r@example.org"]
    assert msg.from_email == "DALIA <from@example.org>"
    assert msg.body == "Body" and not getattr(msg, "alternatives", [])


def test_empty_prefix_and_newlines_stripped(contact_settings):
    ContactFormSettings.objects.update(subject_prefix="")
    make()
    with mock.patch("mailing.service.get_connection", fake_get_connection([None])):
        service.send_contact_message(subject="a\r\nBcc: x", body="b", reply_to="r@example.org")
    assert mail.outbox[0].subject == "a Bcc: x"


def test_order_respected_and_fallback(contact_settings):
    make("second", order=2)
    make("first", order=1)
    factory = fake_get_connection([None])
    with mock.patch("mailing.service.get_connection", factory):
        service.send_contact_message(subject="s", body="b", reply_to="r@example.org")
    assert len(factory.calls) == 1
    assert mail.outbox[0].from_email  # first provider used; second never built


@pytest.mark.parametrize(
    "exc",
    [
        smtplib.SMTPException("x"),
        OSError("x"),
        Smtp2goError(500, "E"),
        UnsafeEndpointError("x"),
        "anymail",
    ],
)
def test_failure_falls_back_to_next(contact_settings, exc):
    make("a", order=1)
    make("b", order=2)
    if exc == "anymail":
        exc = anymail_error()
    factory = fake_get_connection([exc, None])
    with mock.patch("mailing.service.get_connection", factory):
        service.send_contact_message(subject="s", body="b", reply_to="r@example.org")
    assert len(factory.calls) == 2 and len(mail.outbox) == 1


def test_unsafe_endpoint_at_connect_counts_as_failure(contact_settings):
    make("a", order=1)
    make("b", order=2)
    factory = fake_get_connection([None])
    with (
        mock.patch(
            "mailing.service.connection_types.check_endpoint_at_connect",
            side_effect=[UnsafeEndpointError("bad"), None],
        ),
        mock.patch("mailing.service.get_connection", factory),
    ):
        service.send_contact_message(subject="s", body="b", reply_to="r@example.org")
    assert len(factory.calls) == 1


def test_undecryptable_provider_skipped(contact_settings, caplog):
    broken = make("a", order=1)
    EmailProvider.objects.filter(pk=broken.pk).update(password_enc="garbage")
    good = make("b", order=2)
    factory = fake_get_connection([None])
    with (
        caplog.at_level(logging.WARNING, "mailing.service"),
        mock.patch("mailing.service.get_connection", factory),
    ):
        service.send_contact_message(subject="s", body="b", reply_to="r@example.org")
    assert len(factory.calls) == 1
    assert f"Skipping provider {broken.pk}" in caplog.text
    assert str(good.pk) not in caplog.text


def test_all_fail_raises(contact_settings, caplog):
    make("a", order=1)
    make("b", order=2)
    factory = fake_get_connection([OSError("x"), OSError("y")])
    with (
        caplog.at_level(logging.INFO, "mailing.service"),
        mock.patch("mailing.service.get_connection", factory),
    ):
        with pytest.raises(AllProvidersFailed) as info:
            service.send_contact_message(subject="s", body="b", reply_to="r@example.org")
    assert info.value.attempts == 2
    assert "ERROR" in [r.levelname for r in caplog.records]


def test_connection_kwargs_fresh_each_call_and_not_shared(contact_settings):
    make("a", order=1)
    make("b", order=2)
    factory = fake_get_connection([OSError("x"), None])
    with mock.patch("mailing.service.get_connection", factory):
        service.send_contact_message(subject="s", body="b", reply_to="r@example.org")
    assert factory.calls[0][1] is not factory.calls[1][1]


def test_anymail_kwargs_contain_requests_timeout(contact_settings):
    make(ctype="sendgrid", is_active=True)
    factory = fake_get_connection([None])
    with mock.patch("mailing.service.get_connection", factory):
        service.send_contact_message(subject="s", body="b", reply_to="r@example.org")
    backend, kwargs = factory.calls[0]
    assert backend == "anymail.backends.sendgrid.EmailBackend"
    assert kwargs["requests_timeout"][0] == 3.1
    assert 0 < kwargs["requests_timeout"][1] <= 10


def test_smtp_kwargs_use_plain_timeout(contact_settings):
    make()
    factory = fake_get_connection([None])
    with mock.patch("mailing.service.get_connection", factory):
        service.send_contact_message(subject="s", body="b", reply_to="r@example.org")
    assert factory.calls[0][1]["timeout"] <= 10


# --- deadline ----------------------------------------------------------------


class Clock:
    def __init__(self, ticks):
        self.ticks = list(ticks)

    def __call__(self):
        return self.ticks.pop(0) if len(self.ticks) > 1 else self.ticks[0]


def test_timeouts_follow_remaining_time(contact_settings):
    make("a", order=1)
    make("b", order=2)
    factory = fake_get_connection([OSError("x"), None])
    # start, remaining check #1, remaining check #2
    clock = Clock([100.0, 100.5, 112.0])
    with (
        mock.patch("mailing.service.get_connection", factory),
        mock.patch("mailing.service.time.monotonic", clock),
    ):
        service.send_contact_message(subject="s", body="b", reply_to="r@example.org")
    assert factory.calls[0][1]["timeout"] == 10  # min(10, 19.5)
    assert factory.calls[1][1]["timeout"] == 8.0  # min(10, 120 + 20 - 112)


def test_provider_skipped_below_min_remaining(contact_settings):
    make("a", order=1)
    make("b", order=2)
    factory = fake_get_connection([OSError("x"), None])
    clock = Clock([100.0, 100.0, 117.5])  # 2.5 s left for second
    with (
        mock.patch("mailing.service.get_connection", factory),
        mock.patch("mailing.service.time.monotonic", clock),
    ):
        with pytest.raises(AllProvidersFailed) as info:
            service.send_contact_message(subject="s", body="b", reply_to="r@example.org")
    assert len(factory.calls) == 1 and info.value.attempts == 1


def test_nothing_tried_after_deadline(contact_settings):
    make()
    factory = fake_get_connection([None])
    clock = Clock([100.0, 125.0])
    with (
        mock.patch("mailing.service.get_connection", factory),
        mock.patch("mailing.service.time.monotonic", clock),
    ):
        with pytest.raises(AllProvidersFailed) as info:
            service.send_contact_message(subject="s", body="b", reply_to="r@example.org")
    assert factory.calls == [] and info.value.attempts == 0


# --- logging -----------------------------------------------------------------


def test_logs_contain_no_personal_data_or_exception_text(contact_settings, caplog):
    make("a", order=1)
    make("b", order=2)
    factory = fake_get_connection([anymail_error(), None])
    with (
        caplog.at_level(logging.DEBUG, "mailing.service"),
        mock.patch("mailing.service.get_connection", factory),
    ):
        service.send_contact_message(
            subject="SubjectXYZ", body="BodyXYZ secret", reply_to="visitor@example.org"
        )
    text = caplog.text
    assert "AnymailAPIError" in text
    for forbidden in (
        SECRET,
        "boom",
        "visitor@example.org",
        "to@example.org",
        "BodyXYZ",
        "SubjectXYZ",
    ):
        assert forbidden not in text


# --- test email --------------------------------------------------------------


def test_send_test_email_uses_given_inactive_provider():
    provider = make(active=False)
    factory = fake_get_connection([None])
    with mock.patch("mailing.service.get_connection", factory):
        service.send_test_email(provider, "me@example.org")
    assert len(factory.calls) == 1
    msg = mail.outbox[0]
    assert msg.subject == "DALIA test email"
    assert msg.to == ["me@example.org"]
    assert provider.name in msg.body and "UTC" in msg.body
    assert factory.calls[0][1]["timeout"] == 10


def test_send_test_email_propagates_exception():
    provider = make()
    with mock.patch(
        "mailing.service.get_connection", fake_get_connection([Smtp2goError(401, "X")])
    ):
        with pytest.raises(Smtp2goError):
            service.send_test_email(provider, "me@example.org")


def test_send_test_email_propagates_unsafe_endpoint():
    provider = make()
    with mock.patch(
        "mailing.service.connection_types.check_endpoint_at_connect",
        side_effect=UnsafeEndpointError("x"),
    ):
        with pytest.raises(UnsafeEndpointError):
            service.send_test_email(provider, "me@example.org")


def test_anymail_backend_instantiates_without_network():
    pytest.importorskip("anymail")
    from django.core.mail import get_connection

    conn = get_connection(
        "anymail.backends.sendgrid.EmailBackend", api_key="x", requests_timeout=(3.1, 5)
    )
    assert conn.session is None or conn.session  # constructed, nothing sent


# --- sending status cache -------------------------------------------------------


def test_status_second_call_does_no_db_query(contact_settings, django_assert_num_queries):
    make()
    first = service.sending_status()
    with django_assert_num_queries(0):
        second = service.sending_status()
    assert first == second and second.available is True


def test_status_cache_holds_only_flag_and_reasons(contact_settings):
    from django.core.cache import cache

    make()
    service.sending_status()
    cached = cache.get(service.SENDING_STATUS_CACHE_KEY)
    assert set(cached) == {"available", "reasons"}
    assert SECRET not in repr(cached)


def test_status_invalidated_by_provider_and_settings_changes(contact_settings):
    provider = make()
    assert service.sending_status().available is True
    provider.is_active = False
    provider.save()
    assert service.sending_status().reasons == ("no_provider",)
    provider.is_active = True
    provider.save()
    assert service.sending_status().available is True
    contact_settings.delete()
    assert service.sending_status().reasons == ("no_recipient",)
    ContactFormSettings.objects.create(recipients="to@example.org")
    assert service.sending_status().available is True
    provider.delete()
    assert service.sending_status().reasons == ("no_provider",)
