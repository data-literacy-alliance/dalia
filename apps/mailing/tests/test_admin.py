import secrets
import socket
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.core.cache import cache
from django.test import Client, override_settings
from django.urls import NoReverseMatch, resolve, reverse
from mailing import connection_types as ct
from mailing import crypto
from mailing.exceptions import Smtp2goError
from mailing.models import ContactFormSettings, EmailProvider

GAI = "mailing.connection_types.socket.getaddrinfo"
PUBLIC = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]
PRIVATE = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.10", 0))]
SECRET = "PLAINTEXT-SECRET-1234567890"

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _key(tmp_path):
    path = tmp_path / "key"
    path.write_text(secrets.token_hex(32))
    crypto._reset_cache()
    cache.clear()
    with override_settings(EMAIL_FERNET_KEY_FILE=str(path)):
        yield path
    crypto._reset_cache()


@pytest.fixture(autouse=True)
def _dns():
    with mock.patch(GAI, return_value=PUBLIC) as m:
        yield m


@pytest.fixture
def su_client(admin_user):
    client = Client()
    client.force_login(admin_user)
    return client


@pytest.fixture
def staff_client(db):
    user = User.objects.create_user(
        username="staffer", email="s@example.org", password="x", is_staff=True
    )
    user.user_permissions.set(Permission.objects.filter(content_type__app_label="mailing"))
    client = Client()
    client.force_login(user)
    return client


def make_provider(**kw):
    data = {
        "name": "P1",
        "connection_type": "smtp",
        "host": "mail.example.org",
        "port": 587,
        "from_email": "a@example.org",
    }
    data.update(kw)
    return EmailProvider.objects.create(**data)


def smtp_post(**kw):
    data = {
        "name": "P1",
        "connection_type": "smtp",
        "host": "mail.example.org",
        "port": "587",
        "security": "starttls",
        "username": "",
        "api_url": "",
        "from_email": "a@example.org",
        "from_name": "",
        "order": "0",
        "password_new": "",
    }
    data.update(kw)
    return data


def msgs(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


# --- permissions ---------------------------------------------------------------


def test_staff_non_superuser_denied_everywhere(staff_client):
    provider = make_provider()
    urls = [
        reverse("admin:mailing_emailprovider_changelist"),
        reverse("admin:mailing_emailprovider_add"),
        reverse("admin:mailing_emailprovider_change", args=[provider.pk]),
        reverse("admin:mailing_emailprovider_delete", args=[provider.pk]),
        reverse("admin:mailing_emailprovider_send_test", args=[provider.pk]),
    ]
    for url in urls:
        assert staff_client.get(url).status_code == 403, url
    assert staff_client.post(urls[-1], {"email": "x@example.org"}).status_code == 403
    index = staff_client.get(reverse("admin:index"))
    assert b"mailing/emailprovider" not in index.content


def test_superuser_sees_provider_in_changelist(su_client):
    make_provider()
    response = su_client.get(reverse("admin:mailing_emailprovider_changelist"))
    assert response.status_code == 200
    assert b"P1" in response.content


def test_no_import_export_urls(su_client):
    for name in ("admin:mailing_emailprovider_import", "admin:mailing_emailprovider_export"):
        with pytest.raises(NoReverseMatch):
            reverse(name)
    # Django's catch-all only redirects "<id>/" to "<id>/change/"; no import view exists.
    response = su_client.get("/admin/mailing/emailprovider/import/", follow=True)
    assert "import" not in resolve("/admin/mailing/emailprovider/import/").func.__name__
    assert response.redirect_chain  # only the generic "<id>/" -> "<id>/change/" redirect


# --- secrets -------------------------------------------------------------------


def test_secret_stored_encrypted_and_never_rendered(su_client):
    response = su_client.post(
        reverse("admin:mailing_emailprovider_add"), smtp_post(username="u", password_new=SECRET)
    )
    assert response.status_code == 302, response.content[:2000]
    provider = EmailProvider.objects.get()
    assert provider.password_enc and provider.password_enc != SECRET
    assert provider.get_secret("password_enc") == SECRET
    assert provider.is_active is False
    change = su_client.get(reverse("admin:mailing_emailprovider_change", args=[provider.pk]))
    html = change.content.decode()
    assert SECRET not in html
    assert provider.password_enc not in html
    assert "currently set" in html


def test_secret_not_rendered_after_failed_post(su_client):
    response = su_client.post(
        reverse("admin:mailing_emailprovider_add"),
        smtp_post(host="", password_new=SECRET),
    )
    assert response.status_code == 200
    assert SECRET not in response.content.decode()


def test_clear_secret(su_client):
    provider = make_provider(username="u")
    provider.set_secret("password", SECRET)
    provider.save()
    data = smtp_post(username="u", clear_password="on")
    response = su_client.post(
        reverse("admin:mailing_emailprovider_change", args=[provider.pk]), data
    )
    assert response.status_code == 302
    provider.refresh_from_db()
    assert provider.password_enc == ""


def test_clear_and_new_conflict(su_client):
    response = su_client.post(
        reverse("admin:mailing_emailprovider_add"),
        smtp_post(password_new=SECRET, clear_password="on"),
    )
    assert response.status_code == 200
    assert EmailProvider.objects.count() == 0


def test_blank_secret_keeps_stored(su_client):
    provider = make_provider(username="u")
    provider.set_secret("password", SECRET)
    provider.save()
    response = su_client.post(
        reverse("admin:mailing_emailprovider_change", args=[provider.pk]),
        smtp_post(username="u", from_name="New"),
    )
    assert response.status_code == 302
    provider.refresh_from_db()
    assert provider.get_secret("password") == SECRET


def test_secret_with_missing_key_is_form_error(su_client, _key):
    _key.write_text("nothex")
    crypto._reset_cache()
    response = su_client.post(
        reverse("admin:mailing_emailprovider_add"), smtp_post(username="u", password_new=SECRET)
    )
    assert response.status_code == 200
    assert "Encryption key not available" in response.content.decode()
    assert EmailProvider.objects.count() == 0


# --- required kwargs / endpoint ------------------------------------------------

API_TYPES = [t for t in ct.CONNECTION_TYPES if t != "smtp"]


@pytest.mark.parametrize("ctype", list(ct.CONNECTION_TYPES))
def test_missing_required_value_per_type(su_client, ctype):
    data = {
        "name": "X",
        "connection_type": ctype,
        "security": "starttls",
        "from_email": "a@example.org",
        "order": "0",
    }
    response = su_client.post(reverse("admin:mailing_emailprovider_add"), data)
    assert response.status_code == 200
    assert EmailProvider.objects.count() == 0


@pytest.mark.parametrize("ctype", ["sendgrid", "mailjet", "scaleway", "mailgun"])
def test_api_type_saves_with_all_required(su_client, ctype):
    fields = ct.required_fields(ctype)
    data = {
        "name": "X",
        "connection_type": ctype,
        "security": "starttls",
        "from_email": "a@example.org",
        "order": "0",
    }
    if "api_key_enc" in fields:
        data["api_key_new"] = "key-1"
    if "secret_enc" in fields:
        data["secret_new"] = "secret-1"
    if "project_id" in fields:
        data["project_id"] = "proj"
    response = su_client.post(reverse("admin:mailing_emailprovider_add"), data)
    assert response.status_code == 302, response.content[:1500]
    provider = EmailProvider.objects.get()
    assert provider.credentials_status() == "ok"


def test_inapplicable_secret_rejected(su_client):
    response = su_client.post(
        reverse("admin:mailing_emailprovider_add"), smtp_post(api_key_new="nope")
    )
    assert response.status_code == 200
    assert EmailProvider.objects.count() == 0


def test_private_smtp_host_rejected(su_client, _dns):
    _dns.return_value = PRIVATE
    response = su_client.post(reverse("admin:mailing_emailprovider_add"), smtp_post())
    assert response.status_code == 200
    assert EmailProvider.objects.count() == 0


def test_non_https_api_url_rejected(su_client):
    data = {
        "name": "X",
        "connection_type": "sendgrid",
        "security": "starttls",
        "from_email": "a@example.org",
        "order": "0",
        "api_key_new": "k",
        "api_url": "http://api.sendgrid.com",
    }
    response = su_client.post(reverse("admin:mailing_emailprovider_add"), data)
    assert response.status_code == 200
    assert EmailProvider.objects.count() == 0


def test_security_none_with_password_rejected(su_client):
    response = su_client.post(
        reverse("admin:mailing_emailprovider_add"),
        smtp_post(security="none", username="u", password_new="p"),
    )
    assert response.status_code == 200
    assert EmailProvider.objects.count() == 0


# --- endpoint change -----------------------------------------------------------


def test_host_change_without_reentry_is_error(su_client):
    provider = make_provider(host="old.example.org", username="u")
    provider.set_secret("password", SECRET)
    provider.save()
    response = su_client.post(
        reverse("admin:mailing_emailprovider_change", args=[provider.pk]),
        smtp_post(host="new.example.org", username="u"),
    )
    assert response.status_code == 200
    assert "re-enter the credentials" in response.content.decode()
    provider.refresh_from_db()
    assert provider.host == "old.example.org"
    assert provider.get_secret("password") == SECRET


def test_host_change_with_reentry_saves_new_secret(su_client):
    provider = make_provider(host="old.example.org", username="u")
    provider.set_secret("password", SECRET)
    provider.save()
    response = su_client.post(
        reverse("admin:mailing_emailprovider_change", args=[provider.pk]),
        smtp_post(host="new.example.org", username="u", password_new="fresh-pass"),
    )
    assert response.status_code == 302
    provider.refresh_from_db()
    assert provider.host == "new.example.org"
    assert provider.get_secret("password") == "fresh-pass"


def test_host_change_with_explicit_clear_drops_optional_secret(su_client):
    provider = make_provider(host="old.example.org", username="u")
    provider.set_secret("password", SECRET)
    provider.save()
    response = su_client.post(
        reverse("admin:mailing_emailprovider_change", args=[provider.pk]),
        smtp_post(host="new.example.org", username="u", clear_password="on"),
    )
    # smtp requires only host/port, so the optional password may be dropped explicitly
    assert response.status_code == 302
    provider.refresh_from_db()
    assert provider.password_enc == ""


# --- badge, actions, banners ----------------------------------------------------


def test_credentials_badge_and_actions(su_client):
    provider = make_provider()
    url = reverse("admin:mailing_emailprovider_changelist")
    response = su_client.post(
        url, {"action": "activate_providers", "_selected_action": [provider.pk]}, follow=True
    )
    assert response.status_code == 200
    provider.refresh_from_db()
    assert provider.is_active is True
    su_client.post(url, {"action": "deactivate_providers", "_selected_action": [provider.pk]})
    provider.refresh_from_db()
    assert provider.is_active is False


@pytest.mark.parametrize("content", ["", "nothex"])
def test_key_banner_when_key_missing_or_invalid(su_client, _key, content):
    _key.write_text(content)
    crypto._reset_cache()
    for name in ("admin:mailing_emailprovider_changelist", "admin:mailing_emailprovider_add"):
        response = su_client.get(reverse(name))
        assert any("dalia20_email_fernet_key" in m for m in msgs(response))


def test_no_banner_with_valid_key(su_client):
    response = su_client.get(reverse("admin:mailing_emailprovider_changelist"))
    assert not any("encryption key" in m for m in msgs(response))


def test_reenter_banner_for_active_provider(su_client, _key):
    provider = make_provider(connection_type="sendgrid", host="", port=None, is_active=True)
    provider.set_secret("api_key", "k")
    provider.save()
    _key.write_text(secrets.token_hex(32))  # key rotated
    crypto._reset_cache()
    response = su_client.get(reverse("admin:mailing_emailprovider_changelist"))
    assert any("must be re-entered" in m for m in msgs(response))
    assert "must be re-entered" in response.content.decode()  # badge


# --- test email ----------------------------------------------------------------


def send_url(provider):
    return reverse("admin:mailing_emailprovider_send_test", args=[provider.pk])


def test_send_test_get_anonymous_redirects_to_login():
    provider = make_provider()
    response = Client().get(send_url(provider))
    assert response.status_code == 302
    assert "login" in response["Location"]


def test_send_test_get_form(su_client):
    provider = make_provider()
    response = su_client.get(send_url(provider))
    assert response.status_code == 200
    assert b"csrfmiddlewaretoken" in response.content


def test_send_test_post_requires_csrf(admin_user):
    provider = make_provider()
    client = Client(enforce_csrf_checks=True)
    client.force_login(admin_user)
    with mock.patch("mailing.service.send_test_email") as send:
        response = client.post(send_url(provider), {"email": "x@example.org"})
    assert response.status_code == 403
    send.assert_not_called()


def test_send_test_calls_service_with_inactive_provider(su_client):
    provider = make_provider(is_active=False)
    with mock.patch("mailing.service.send_test_email") as send:
        response = su_client.post(send_url(provider), {"email": "x@example.org"})
    assert response.status_code == 302
    assert response["Location"].endswith(
        reverse("admin:mailing_emailprovider_change", args=[provider.pk])
    )
    send.assert_called_once()
    assert send.call_args.args[0].pk == provider.pk
    assert send.call_args.args[1] == "x@example.org"
    assert any("Test email sent" in m for m in msgs(response))


def test_send_test_invalid_address_not_sent(su_client):
    provider = make_provider()
    with mock.patch("mailing.service.send_test_email") as send:
        response = su_client.post(send_url(provider), {"email": "not-an-email"})
    assert response.status_code == 200
    send.assert_not_called()


def test_send_test_error_is_redacted(su_client):
    provider = make_provider(connection_type="sendgrid", host="", port=None)
    provider.set_secret("api_key", SECRET)
    provider.save()
    exc = RuntimeError(f"401 unauthorized for key {SECRET}")
    exc.status_code = 401
    with mock.patch("mailing.service.send_test_email", side_effect=exc):
        response = su_client.post(send_url(provider), {"email": "x@example.org"})
    text = " ".join(msgs(response))
    assert "RuntimeError (HTTP 401)" in text
    assert SECRET not in text
    assert "unauthorized" not in text


def test_send_test_smtp2go_status_and_smtp_code(su_client):
    provider = make_provider()
    with mock.patch(
        "mailing.service.send_test_email", side_effect=Smtp2goError(status=403, error_code="E")
    ):
        response = su_client.post(send_url(provider), {"email": "x@example.org"})
    assert any("Smtp2goError (HTTP 403)" in m and "E_" not in m for m in msgs(response))

    exc = OSError("boom")
    exc.smtp_code = 535
    with mock.patch("mailing.service.send_test_email", side_effect=exc):
        response = su_client.post(send_url(provider), {"email": "x@example.org"})
    assert any("OSError (SMTP 535)" in m and "boom" not in m for m in msgs(response))


def test_describe_error_redacts_stored_secrets():
    from mailing.admin import describe_send_error

    provider = make_provider(connection_type="sendgrid", host="", port=None)
    provider.set_secret("api_key", "Runtime")  # pathological: secret inside the class name
    assert describe_send_error(RuntimeError("m"), provider) == "***Error"


def test_send_test_rate_limit(su_client):
    provider = make_provider()
    with (
        override_settings(MAILING_TEST_EMAIL_LIMIT_PER_HOUR=10),
        mock.patch("mailing.service.send_test_email") as send,
    ):
        for _ in range(10):
            su_client.post(send_url(provider), {"email": "x@example.org"})
        assert send.call_count == 10
        response = su_client.post(send_url(provider), {"email": "x@example.org"})
    assert send.call_count == 10
    assert any("Too many test emails" in m for m in msgs(response))


# --- contact form settings -----------------------------------------------------


def test_settings_changelist_redirects_to_add_then_change(su_client):
    response = su_client.get(reverse("admin:mailing_contactformsettings_changelist"))
    assert response.status_code == 302
    assert response["Location"] == reverse("admin:mailing_contactformsettings_add")
    obj = ContactFormSettings.objects.create(recipients="a@example.org")
    response = su_client.get(reverse("admin:mailing_contactformsettings_changelist"))
    assert response["Location"] == reverse(
        "admin:mailing_contactformsettings_change", args=[obj.pk]
    )


def test_settings_add_once_and_not_deletable(su_client):
    url = reverse("admin:mailing_contactformsettings_add")
    with mock.patch(
        "mailing.service.sending_status",
        return_value=mock.Mock(available=False, reasons=("no_provider",)),
    ):
        response = su_client.post(
            url,
            {
                "recipients": "a@example.org\n\nb@example.org\na@example.org",
                "subject_prefix": "[D]",
            },
        )
        assert response.status_code == 302
        obj = ContactFormSettings.objects.get()
        assert obj.recipient_list() == ["a@example.org", "b@example.org"]
        assert su_client.get(url).status_code == 403
        assert (
            su_client.get(
                reverse("admin:mailing_contactformsettings_delete", args=[obj.pk])
            ).status_code
            == 403
        )
        change = su_client.get(reverse("admin:mailing_contactformsettings_change", args=[obj.pk]))
    assert change.status_code == 200
    assert "no active provider" in change.content.decode()


def test_settings_invalid_recipient(su_client):
    response = su_client.post(
        reverse("admin:mailing_contactformsettings_add"), {"recipients": "bad address"}
    )
    assert response.status_code == 200
    assert ContactFormSettings.objects.count() == 0


def test_activate_deactivate_actions_invalidate_status_cache(su_client):
    from mailing import service

    provider = make_provider()
    url = reverse("admin:mailing_emailprovider_changelist")
    for action in ("activate_providers", "deactivate_providers"):
        service.sending_status()
        assert cache.get(service.SENDING_STATUS_CACHE_KEY) is not None
        su_client.post(url, {"action": action, "_selected_action": [provider.pk]})
        assert cache.get(service.SENDING_STATUS_CACHE_KEY) is None, action
