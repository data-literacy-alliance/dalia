import secrets

import pytest
from django.test import override_settings
from mailing import connection_types as ct
from mailing import crypto
from mailing.exceptions import MailingError
from mailing.models import EmailProvider


@pytest.fixture(autouse=True)
def _key(tmp_path):
    path = tmp_path / "key"
    path.write_text(secrets.token_hex(32))
    crypto._reset_cache()
    with override_settings(EMAIL_FERNET_KEY_FILE=str(path)):
        yield
    crypto._reset_cache()


# Contract table: type -> (backend, required kwargs, optional kwargs)
CONTRACT = {
    "smtp": (
        "django.core.mail.backends.smtp.EmailBackend",
        ["host", "port"],
        ["username", "password", "security"],
    ),
    "mailgun": ("anymail.backends.mailgun.EmailBackend", ["api_key"], ["sender_domain", "api_url"]),
    "postmark": (
        "anymail.backends.postmark.EmailBackend",
        ["server_token"],
        ["message_stream", "api_url"],
    ),
    "sendgrid": ("anymail.backends.sendgrid.EmailBackend", ["api_key"], ["api_url"]),
    "mailjet": ("anymail.backends.mailjet.EmailBackend", ["api_key", "secret_key"], ["api_url"]),
    "mandrill": ("anymail.backends.mandrill.EmailBackend", ["api_key"], ["api_url"]),
    "brevo": ("anymail.backends.brevo.EmailBackend", ["api_key"], ["api_url"]),
    "sparkpost": (
        "anymail.backends.sparkpost.EmailBackend",
        ["api_key"],
        ["subaccount", "api_url"],
    ),
    "resend": ("anymail.backends.resend.EmailBackend", ["api_key"], ["api_url"]),
    "mailersend": ("anymail.backends.mailersend.EmailBackend", ["api_token"], ["api_url"]),
    "mailtrap": (
        "anymail.backends.mailtrap.EmailBackend",
        ["api_token"],
        ["sandbox_id", "api_url"],
    ),
    "postal": ("anymail.backends.postal.EmailBackend", ["api_key", "api_url"], []),
    "scaleway": (
        "anymail.backends.scaleway.EmailBackend",
        ["secret_key", "project_id"],
        ["region", "api_url"],
    ),
    "unisender_go": ("anymail.backends.unisender_go.EmailBackend", ["api_key", "api_url"], []),
    "smtp2go_api": ("mailing.backends.smtp2go.EmailBackend", ["api_key"], ["api_url"]),
}

# kwarg -> (field, value) used to fill a provider; secrets are set via set_secret.
VALUES = {
    "host": "mail.example.org",
    "port": 587,
    "username": "user",
    "password": "pw-secret",
    "api_key": "key-secret",
    "server_token": "key-secret",
    "api_token": "key-secret",
    "secret_key": "sec-secret",
    "sender_domain": "mg.example.org",
    "message_stream": "outbound",
    "subaccount": "sub",
    "sandbox_id": "123",
    "project_id": "proj",
    "region": "fr-par",
    "api_url": "https://api.example.org/v3/send",
}


def make_provider(ctype):
    provider = EmailProvider(name=ctype, connection_type=ctype, from_email="a@example.org")
    spec = ct.CONNECTION_TYPES[ctype]
    for kwarg in spec.required + spec.optional:
        if kwarg == "security":
            continue
        field = ct.FIELD_MAP[kwarg]
        if field in ct.SECRET_FIELDS:
            provider.set_secret(field, VALUES[kwarg])
        else:
            setattr(provider, field, VALUES[kwarg])
    return provider


def test_registry_matches_contract_table():
    assert set(ct.CONNECTION_TYPES) == set(CONTRACT)
    for ctype, (backend, required, optional) in CONTRACT.items():
        spec = ct.CONNECTION_TYPES[ctype]
        assert spec.backend == backend
        assert list(spec.required) == required
        assert list(spec.optional) == optional


def test_api_hosts_contract():
    assert ct.CONNECTION_TYPES["smtp"].api_hosts == ()
    assert ct.CONNECTION_TYPES["postal"].api_hosts == ()
    assert ct.CONNECTION_TYPES["postal"].requires_custom_endpoint
    assert "api.eu.mailgun.net" in ct.CONNECTION_TYPES["mailgun"].api_hosts
    assert "eu-api.smtp2go.com" in ct.CONNECTION_TYPES["smtp2go_api"].api_hosts


@pytest.mark.parametrize("ctype", sorted(CONTRACT))
def test_build_kwargs_exact_keys_and_timeout(ctype):
    _, required, optional = CONTRACT[ctype]
    kwargs = ct.build_connection_kwargs(make_provider(ctype), timeout=7.5)
    expected = {k for k in required + optional if k != "security"}
    if ctype == "smtp":
        assert set(kwargs) == expected | {"use_tls", "use_ssl", "timeout"}
        assert kwargs["timeout"] == 7.5
        assert kwargs["use_tls"] is True and kwargs["use_ssl"] is False
    elif ctype == "smtp2go_api":
        assert set(kwargs) == expected | {"timeout"}
        assert kwargs["timeout"] == (3.1, 7.5)
    else:
        assert set(kwargs) == expected | {"requests_timeout"}
        assert kwargs["requests_timeout"] == (3.1, 7.5)
    for key in expected:
        assert kwargs[key] == VALUES[key]  # secrets decrypted


@pytest.mark.parametrize(
    "security,tls,ssl", [("starttls", True, False), ("ssl", False, True), ("none", False, False)]
)
def test_smtp_security_mapping(security, tls, ssl):
    provider = make_provider("smtp")
    provider.security = security
    kwargs = ct.build_connection_kwargs(provider, timeout=5)
    assert (kwargs["use_tls"], kwargs["use_ssl"]) == (tls, ssl)


def test_optional_empty_values_omitted():
    provider = make_provider("smtp")
    provider.username = ""
    provider.clear_secret("password")
    kwargs = ct.build_connection_kwargs(provider, timeout=5)
    assert "username" not in kwargs and "password" not in kwargs


def test_missing_required_raises_without_secret_in_message():
    provider = make_provider("mailjet")
    provider.clear_secret("secret")
    with pytest.raises(MailingError):
        ct.build_connection_kwargs(provider, timeout=5)


def test_fresh_dict_per_call():
    provider = make_provider("sendgrid")
    first = ct.build_connection_kwargs(provider, timeout=5)
    first["api_key"] = "tampered"
    first["extra"] = 1
    second = ct.build_connection_kwargs(provider, timeout=5)
    assert second["api_key"] == "key-secret"
    assert "extra" not in second
    assert first is not second


def test_required_and_allowed_fields():
    assert ct.required_fields("mailjet") == ("api_key_enc", "secret_enc")
    assert ct.required_fields("smtp") == ("host", "port")
    assert "password_enc" in ct.allowed_fields("smtp")
    assert ct.allowed_fields("postmark") == ("api_key_enc", "message_stream", "api_url")
    with pytest.raises(MailingError):
        ct.required_fields("nope")
