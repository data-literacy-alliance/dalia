"""Registry of email connection types, kwargs building and endpoint rules.

Backend classes are referenced by dotted path only; anymail is never imported
here. Field names in ``required``/``optional`` are the backend kwarg names;
``FIELD_MAP`` maps a kwarg to the ``EmailProvider`` model field holding it.
"""

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.views.decorators.debug import sensitive_variables

from .exceptions import MailingError, UnsafeEndpointError

CONNECT_TIMEOUT = 3.1
SMTP_PORT_ALLOWLIST = frozenset({25, 465, 587, 2525})

# kwarg name -> EmailProvider model field
FIELD_MAP = {
    "host": "host",
    "port": "port",
    "username": "username",
    "password": "password_enc",
    "security": "security",
    "api_key": "api_key_enc",
    "server_token": "api_key_enc",
    "api_token": "api_key_enc",
    "secret_key": "secret_enc",
    "sender_domain": "sender_domain",
    "region": "region",
    "project_id": "project_id",
    "message_stream": "message_stream",
    "subaccount": "subaccount",
    "sandbox_id": "sandbox_id",
    "api_url": "api_url",
}

SECRET_FIELDS = ("password_enc", "api_key_enc", "secret_enc")

# Model fields that make up the endpoint; changing any clears stored secrets.
ENDPOINT_FIELDS = ("connection_type", "host", "port", "security", "username", "api_url")

# Non-secret option fields that must be empty when the type does not use them.
OPTION_FIELDS = (
    "host",
    "port",
    "username",
    "sender_domain",
    "region",
    "project_id",
    "message_stream",
    "subaccount",
    "sandbox_id",
    "api_url",
)

# Addresses that are blocked in addition to everything not globally routable.
_BLOCKED_NETWORKS = tuple(
    ipaddress.ip_network(n) for n in ("100.64.0.0/10", "10.88.0.0/16")
)


@dataclass(frozen=True)
class ConnectionType:
    label: str
    backend: str
    required: tuple[str, ...]
    optional: tuple[str, ...] = ()
    api_hosts: tuple[str, ...] = ()
    timeout_kwarg: str = "requests_timeout"  # "timeout" for smtp / smtp2go_api
    timeout_is_tuple: bool = True
    requires_custom_endpoint: bool = False


_ANYMAIL = "anymail.backends.{}.EmailBackend"


def _esp(label, name, required, optional=(), api_hosts=(), **kw):
    return ConnectionType(
        label=label,
        backend=_ANYMAIL.format(name),
        required=tuple(required),
        optional=tuple(optional),
        api_hosts=tuple(api_hosts),
        **kw,
    )


CONNECTION_TYPES: dict[str, ConnectionType] = {
    "smtp": ConnectionType(
        label="SMTP",
        backend="django.core.mail.backends.smtp.EmailBackend",
        required=("host", "port"),
        optional=("username", "password", "security"),
        timeout_kwarg="timeout",
        timeout_is_tuple=False,
    ),
    "mailgun": _esp(
        "Mailgun API",
        "mailgun",
        ("api_key",),
        ("sender_domain", "api_url"),
        ("api.mailgun.net", "api.eu.mailgun.net"),
    ),
    "postmark": _esp(
        "Postmark API",
        "postmark",
        ("server_token",),
        ("message_stream", "api_url"),
        ("api.postmarkapp.com",),
    ),
    "sendgrid": _esp("SendGrid API", "sendgrid", ("api_key",), ("api_url",), ("api.sendgrid.com",)),
    "mailjet": _esp(
        "Mailjet API", "mailjet", ("api_key", "secret_key"), ("api_url",), ("api.mailjet.com",)
    ),
    "mandrill": _esp("Mandrill API", "mandrill", ("api_key",), ("api_url",), ("mandrillapp.com",)),
    "brevo": _esp(
        "Brevo API", "brevo", ("api_key",), ("api_url",), ("api.brevo.com", "api.sendinblue.com")
    ),
    "sparkpost": _esp(
        "SparkPost API",
        "sparkpost",
        ("api_key",),
        ("subaccount", "api_url"),
        ("api.sparkpost.com", "api.eu.sparkpost.com"),
    ),
    "resend": _esp("Resend API", "resend", ("api_key",), ("api_url",), ("api.resend.com",)),
    "mailersend": _esp(
        "MailerSend API", "mailersend", ("api_token",), ("api_url",), ("api.mailersend.com",)
    ),
    "mailtrap": _esp(
        "Mailtrap API",
        "mailtrap",
        ("api_token",),
        ("sandbox_id", "api_url"),
        ("send.api.mailtrap.io", "sandbox.api.mailtrap.io", "bulk.api.mailtrap.io"),
    ),
    "postal": _esp(
        "Postal API (self-hosted)",
        "postal",
        ("api_key", "api_url"),
        (),
        (),
        requires_custom_endpoint=True,
    ),
    "scaleway": _esp(
        "Scaleway API",
        "scaleway",
        ("secret_key", "project_id"),
        ("region", "api_url"),
        ("api.scaleway.com",),
    ),
    "unisender_go": _esp(
        "UniSender Go API",
        "unisender_go",
        ("api_key", "api_url"),
        (),
        ("go1.unisender.ru", "go2.unisender.ru"),
    ),
    "smtp2go_api": ConnectionType(
        label="SMTP2GO API",
        backend="mailing.backends.smtp2go.EmailBackend",
        required=("api_key",),
        optional=("api_url",),
        api_hosts=(
            "api.smtp2go.com",
            "eu-api.smtp2go.com",
            "us-api.smtp2go.com",
            "au-api.smtp2go.com",
        ),
        timeout_kwarg="timeout",
    ),
}

CONNECTION_TYPE_CHOICES = [(key, spec.label) for key, spec in CONNECTION_TYPES.items()]


def _spec(connection_type: str) -> ConnectionType:
    try:
        return CONNECTION_TYPES[connection_type]
    except KeyError:
        raise MailingError(f"Unknown connection type: {connection_type!r}") from None


def _fields_for(kwargs_names) -> tuple[str, ...]:
    fields = []
    for name in kwargs_names:
        field = FIELD_MAP[name]
        if field not in fields:
            fields.append(field)
    return tuple(fields)


def required_fields(connection_type: str) -> tuple[str, ...]:
    """Model field names that must be filled for this type."""
    return _fields_for(_spec(connection_type).required)


def allowed_fields(connection_type: str) -> tuple[str, ...]:
    """Model field names (required + optional) that apply to this type."""
    spec = _spec(connection_type)
    return _fields_for(spec.required + spec.optional)


def _is_set(provider, field: str) -> bool:
    value = getattr(provider, field)
    return value not in (None, "")


@sensitive_variables()
def build_connection_kwargs(provider, *, timeout: float) -> dict:
    """Return a fresh kwargs dict for ``get_connection`` (secrets decrypted)."""
    spec = _spec(provider.connection_type)
    kwargs: dict = {}
    for name in spec.required + spec.optional:
        if name == "security":
            continue
        field = FIELD_MAP[name]
        if field in SECRET_FIELDS:
            value = provider.get_secret(field)
        else:
            value = getattr(provider, field)
        if value in (None, ""):
            if name in spec.required:
                raise MailingError(f"Provider is missing required setting {name!r}")
            continue
        kwargs[name] = value
    if provider.connection_type == "smtp":
        kwargs["use_tls"] = provider.security == "starttls"
        kwargs["use_ssl"] = provider.security == "ssl"
    kwargs[spec.timeout_kwarg] = (CONNECT_TIMEOUT, timeout) if spec.timeout_is_tuple else timeout
    return kwargs


# --- endpoint validation -----------------------------------------------------


def _address_blocked(ip) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    if not ip.is_global:  # loopback, private, link-local, unspecified, reserved, CGNAT, ...
        return True
    if ip.is_multicast or ip.is_reserved:
        return True
    return any(ip in net for net in _BLOCKED_NETWORKS if net.version == ip.version)


def assert_host_is_public(host: str) -> None:
    """Raise UnsafeEndpointError if ``host`` fails to resolve or resolves to a blocked address."""
    try:
        infos = socket.getaddrinfo(host, None)
    except (OSError, UnicodeError):
        raise UnsafeEndpointError(f"Host cannot be resolved: {host}") from None
    if not infos:
        raise UnsafeEndpointError(f"Host cannot be resolved: {host}")
    for info in infos:
        address = str(info[4][0]).split("%", 1)[0]
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            raise UnsafeEndpointError(f"Host resolves to an invalid address: {host}") from None
        if _address_blocked(ip):
            raise UnsafeEndpointError(f"Host resolves to a blocked address: {host}")


def _api_url_errors(provider, spec: ConnectionType) -> list[str]:
    """Structural and allowlist checks on api_url (no DNS)."""
    url = provider.api_url
    if not url:
        return []
    try:
        parts = urlsplit(url)
        hostname = parts.hostname
        parts.port  # noqa: B018 (raises ValueError on a malformed port)
    except ValueError:
        return ["api_url is not a valid URL."]
    if parts.scheme != "https":
        return ["api_url must use https."]
    if not hostname:
        return ["api_url must contain a host."]
    if parts.username is not None or parts.password is not None or "@" in parts.netloc:
        return ["api_url must not contain credentials."]
    if parts.query or parts.fragment:
        return ["api_url must not contain a query or fragment."]
    if not provider.custom_endpoint and hostname.lower() not in spec.api_hosts:
        return ["api_url host is not on the allowlist for this connection type."]
    return []


def _field_errors(provider, spec: ConnectionType) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}

    def add(field, message):
        errors.setdefault(field, []).append(message)

    if spec.requires_custom_endpoint and not provider.custom_endpoint:
        add("custom_endpoint", "This connection type requires a custom endpoint.")
    applicable = set(allowed_fields(provider.connection_type))
    for field in required_fields(provider.connection_type):
        if field not in SECRET_FIELDS and not _is_set(provider, field):
            add(field, "This field is required for this connection type.")
    for field in OPTION_FIELDS:
        if field not in applicable and _is_set(provider, field):
            add(field, "This field does not apply to this connection type.")
    for message in _api_url_errors(provider, spec):
        add("api_url", message)
    if provider.connection_type == "smtp":
        if provider.port is not None and not 1 <= provider.port <= 65535:
            add("port", "Port must be between 1 and 65535.")
        elif (
            provider.port is not None
            and not provider.custom_endpoint
            and provider.port not in SMTP_PORT_ALLOWLIST
        ):
            add("port", "Port must be one of 25, 465, 587, 2525.")
        if provider.security == "none" and (
            provider.username or provider.has_secret("password_enc")
        ):
            add("security", "Security 'none' is only allowed without username and password.")
    return errors


def validate_endpoint(provider) -> None:
    """Save-time validation. Raises ``django.core.exceptions.ValidationError``."""
    spec = _spec(provider.connection_type)
    errors = _field_errors(provider, spec)
    if not errors:
        try:
            _assert_resolves_public(provider, spec)
        except UnsafeEndpointError as exc:
            field = "host" if provider.connection_type == "smtp" else "api_url"
            errors[field] = [str(exc)]
    if errors:
        raise ValidationError(errors)


def _assert_resolves_public(provider, spec: ConnectionType) -> None:
    if provider.connection_type == "smtp":
        assert_host_is_public(provider.host)
    elif provider.custom_endpoint and provider.api_url:
        assert_host_is_public(urlsplit(provider.api_url).hostname)


def check_endpoint_at_connect(provider) -> None:
    """Re-check the endpoint right before connecting. Raises ``UnsafeEndpointError``."""
    spec = _spec(provider.connection_type)
    errors = _field_errors(provider, spec)
    if errors:
        raise UnsafeEndpointError("Provider endpoint violates the endpoint rules")
    _assert_resolves_public(provider, spec)
