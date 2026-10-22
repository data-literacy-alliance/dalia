import secrets
import socket
from unittest import mock

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import override_settings
from mailing import crypto
from mailing.models import ContactFormSettings, EmailProvider

GAI = "mailing.connection_types.socket.getaddrinfo"
PUBLIC = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]


def _use_key(path):
    path.write_text(secrets.token_hex(32))
    crypto._reset_cache()
    return override_settings(EMAIL_FERNET_KEY_FILE=str(path))


@pytest.fixture(autouse=True)
def _key(tmp_path):
    with _use_key(tmp_path / "key"):
        yield
    crypto._reset_cache()


def make(**kw):
    data = {
        "name": "Primary",
        "connection_type": "smtp",
        "host": "mail.example.org",
        "port": 587,
        "username": "u",
        "from_email": "a@example.org",
    }
    data.update(kw)
    return EmailProvider(**data)


def test_defaults_and_str_repr_have_no_secrets():
    provider = make()
    provider.set_secret("password", "hunter2-secret")
    assert provider.is_active is False
    assert str(provider) == "Primary"
    assert "hunter2-secret" not in repr(provider) + str(provider)
    assert "password_enc" not in repr(provider)


@pytest.mark.django_db
def test_secret_stored_encrypted_and_round_trips():
    provider = make()
    provider.set_secret("password", "hunter2-secret")
    provider.save()
    raw = EmailProvider.objects.values_list("password_enc", flat=True).get()
    assert raw and "hunter2-secret" not in raw
    loaded = EmailProvider.objects.get()
    assert loaded.has_secret("password_enc")
    assert loaded.get_secret("password") == "hunter2-secret"
    assert loaded.get_secret("api_key") == ""
    loaded.clear_secret("password")
    assert not loaded.has_secret("password")


def test_unknown_secret_field_rejected():
    with pytest.raises(ValueError):
        make().set_secret("host", "x")


def test_empty_value_clears_secret():
    provider = make()
    provider.set_secret("password", "x")
    provider.set_secret("password", "")
    assert not provider.has_secret("password")


@pytest.mark.django_db
def test_credentials_status(tmp_path):
    provider = make(connection_type="sendgrid", host="", port=None, username="")
    assert provider.credentials_status() == "missing"
    provider.set_secret("api_key", "k")
    assert provider.credentials_status() == "ok"
    provider.save()
    # smtp without password is fine
    assert make().credentials_status() == "ok"
    assert make(host="").credentials_status() == "missing"
    # wrong key -> reenter
    with _use_key(tmp_path / "other"):
        assert EmailProvider.objects.get().credentials_status() == "reenter"


def test_credentials_status_missing_when_key_unavailable(tmp_path):
    provider = make(connection_type="sendgrid", host="", port=None, username="")
    provider.set_secret("api_key", "k")
    crypto._reset_cache()
    with override_settings(EMAIL_FERNET_KEY_FILE=str(tmp_path / "nope")):
        assert provider.credentials_status() == "missing"
    crypto._reset_cache()


@pytest.mark.django_db
def test_endpoint_change_clears_all_secrets():
    provider = make()
    provider.set_secret("password", "pw")
    provider.set_secret("api_key", "k")
    provider.save()
    loaded = EmailProvider.objects.get()
    loaded.host = "other.example.org"
    loaded.save()
    fresh = EmailProvider.objects.get()
    assert not any(fresh.has_secret(f) for f in ("password", "api_key", "secret"))


@pytest.mark.django_db
def test_endpoint_change_with_new_secret_keeps_only_new():
    provider = make()
    provider.set_secret("password", "pw")
    provider.set_secret("api_key", "k")
    provider.save()
    loaded = EmailProvider.objects.get()
    loaded.host = "other.example.org"
    loaded.set_secret("password", "new-pw")
    loaded.save()
    fresh = EmailProvider.objects.get()
    assert fresh.get_secret("password") == "new-pw"
    assert not fresh.has_secret("api_key")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field,value",
    [
        ("port", 465),
        ("security", "ssl"),
        ("username", "x"),
        ("api_url", "https://x.example.org"),
        ("connection_type", "sendgrid"),
    ],
)
def test_each_endpoint_field_clears_secrets(field, value):
    provider = make()
    provider.set_secret("password", "pw")
    provider.save()
    loaded = EmailProvider.objects.get()
    setattr(loaded, field, value)
    loaded.save()
    assert not EmailProvider.objects.get().has_secret("password")


@pytest.mark.django_db
def test_non_endpoint_change_keeps_secrets():
    provider = make()
    provider.set_secret("password", "pw")
    provider.save()
    loaded = EmailProvider.objects.get()
    loaded.from_name = "New name"
    loaded.is_active = True
    loaded.save()
    assert EmailProvider.objects.get().get_secret("password") == "pw"


@pytest.mark.django_db
def test_second_save_after_change_keeps_new_secret():
    provider = make()
    provider.set_secret("password", "pw")
    provider.save()
    loaded = EmailProvider.objects.get()
    loaded.host = "other.example.org"
    loaded.set_secret("password", "pw2")
    loaded.save()
    loaded.from_name = "x"
    loaded.save()
    assert EmailProvider.objects.get().get_secret("password") == "pw2"


@pytest.mark.django_db
def test_update_fields_includes_cleared_secrets():
    provider = make()
    provider.set_secret("password", "pw")
    provider.save()
    loaded = EmailProvider.objects.get()
    loaded.host = "other.example.org"
    loaded.save(update_fields=["host"])
    assert not EmailProvider.objects.get().has_secret("password")


@pytest.mark.django_db
def test_deferred_load_does_not_break():
    make().save()
    loaded = EmailProvider.objects.only("name").get()
    loaded.name = "Renamed"
    loaded.save()


@pytest.mark.django_db
def test_name_unique_and_ordering():
    make(name="B", order=2).save()
    make(name="A", order=1).save()
    assert [p.name for p in EmailProvider.objects.all()] == ["A", "B"]
    with pytest.raises(IntegrityError), transaction.atomic():
        make(name="A").save()


@pytest.mark.django_db
def test_full_clean_validates_endpoint():
    with mock.patch(GAI, return_value=PUBLIC):
        make().full_clean()
    with mock.patch(GAI, return_value=[(socket.AF_INET, 1, 6, "", ("127.0.0.1", 0))]):
        with pytest.raises(ValidationError):
            make().full_clean()


# --- ContactFormSettings -------------------------------------------------------


@pytest.mark.django_db
def test_contact_settings_load_none_when_missing():
    assert ContactFormSettings.load() is None


def test_recipients_cleaned_deduped_and_stripped():
    cfg = ContactFormSettings(recipients=" a@example.org \n\nb@example.org\nA@example.org\n")
    cfg.clean()
    assert cfg.recipients == "a@example.org\nb@example.org"
    assert cfg.recipient_list() == ["a@example.org", "b@example.org"]


def test_recipients_invalid_address_rejected():
    with pytest.raises(ValidationError) as info:
        ContactFormSettings(recipients="a@example.org\nnot-an-email").clean()
    assert "recipients" in info.value.message_dict


def test_recipients_max_20():
    ok = "\n".join(f"u{i}@example.org" for i in range(20))
    ContactFormSettings(recipients=ok).clean()
    with pytest.raises(ValidationError):
        ContactFormSettings(recipients=ok + "\nextra@example.org").clean()


@pytest.mark.django_db
def test_single_row_constraint_and_load():
    ContactFormSettings.objects.create(recipients="a@example.org", subject_prefix="[X]")
    with pytest.raises(IntegrityError), transaction.atomic():
        ContactFormSettings.objects.create(recipients="b@example.org")
    assert ContactFormSettings.load().subject_prefix == "[X]"
