"""Mailing service: ordered provider fallback within a hard deadline.

Known limitation: if a provider times out *after* it already accepted the
message, the next provider is tried and the recipient may get a duplicate.

Logging never contains addresses, bodies, credentials or exception message
text; only provider ids, counts and exception class names.
"""

import logging
import smtplib
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import formataddr

from django.core.cache import cache
from django.core.mail import EmailMessage, get_connection
from django.views.decorators.debug import sensitive_variables

from . import connection_types, crypto
from .connection_types import CONNECTION_TYPES, build_connection_kwargs
from .exceptions import AllProvidersFailed, MailingError, MailingUnavailable
from .models import ContactFormSettings, EmailProvider

logger = logging.getLogger("mailing.service")

SEND_DEADLINE_SECONDS = 20
ATTEMPT_TIMEOUT_MAX = 10
MIN_REMAINING_SECONDS = 3
TEST_EMAIL_SUBJECT = "DALIA test email"
SENDING_STATUS_CACHE_KEY = "mailing:sending_status"
SENDING_STATUS_CACHE_SECONDS = 30


@dataclass(frozen=True)
class SendingStatus:
    available: bool
    reasons: tuple[str, ...]


def _active_providers():
    return EmailProvider.objects.filter(is_active=True).order_by("order", "pk")


def _usable_providers(*, log: bool = True) -> list:
    usable = []
    for provider in _active_providers():
        if provider.credentials_status() == "ok":
            usable.append(provider)
        elif log:
            logger.warning("Skipping provider %s: credentials not usable", provider.pk)
    return usable


def _recipients() -> list[str]:
    settings_row = ContactFormSettings.load()
    return settings_row.recipient_list() if settings_row else []


def invalidate_sending_status() -> None:
    cache.delete(SENDING_STATUS_CACHE_KEY)


def _compute_sending_status() -> SendingStatus:
    reasons = []
    if crypto.key_status() != "ok":
        reasons.append("no_key")
    if not _usable_providers(log=False):
        reasons.append("no_provider")
    if not _recipients():
        reasons.append("no_recipient")
    return SendingStatus(not reasons, tuple(reasons))


def sending_status() -> SendingStatus:
    """Cached for a short time; only the ok flag and reason codes are stored."""
    cached = cache.get(SENDING_STATUS_CACHE_KEY)
    if cached is not None:
        return SendingStatus(cached["available"], tuple(cached["reasons"]))
    status = _compute_sending_status()
    cache.set(
        SENDING_STATUS_CACHE_KEY,
        {"available": status.available, "reasons": list(status.reasons)},
        SENDING_STATUS_CACHE_SECONDS,
    )
    return status


@sensitive_variables()
def _connection_for(provider, timeout: float):
    """Fresh connection (and kwargs dict) for one attempt; endpoint re-checked first."""
    connection_types.check_endpoint_at_connect(provider)
    kwargs = build_connection_kwargs(provider, timeout=timeout)
    return get_connection(CONNECTION_TYPES[provider.connection_type].backend, **kwargs)


def _failure_types() -> tuple[type[BaseException], ...]:
    from anymail.exceptions import AnymailError

    return (AnymailError, smtplib.SMTPException, OSError, MailingError)


def _clean_header(value: str) -> str:
    return " ".join(str(value).replace("\r", " ").replace("\n", " ").split())


def _send_with(provider, *, subject, body, to, timeout, reply_to=None) -> None:
    connection = _connection_for(provider, timeout)
    message = EmailMessage(
        subject,
        body,
        from_email=formataddr((provider.from_name, provider.from_email)),
        to=to,
        reply_to=[reply_to] if reply_to else None,
        connection=connection,
    )
    message.send(fail_silently=False)


def send_contact_message(*, subject: str, body: str, reply_to: str) -> None:
    status = sending_status()
    if not status.available:
        raise MailingUnavailable(status.reasons)
    settings_row = ContactFormSettings.load()
    prefix = settings_row.subject_prefix if settings_row else ""
    full_subject = _clean_header(f"{prefix} {subject}")
    recipients = _recipients()
    failures = _failure_types()
    deadline = time.monotonic() + SEND_DEADLINE_SECONDS
    attempts = 0
    for provider in _usable_providers():
        remaining = deadline - time.monotonic()
        if remaining < MIN_REMAINING_SECONDS:
            break
        attempts += 1
        try:
            _send_with(
                provider,
                subject=full_subject,
                body=body,
                to=recipients,
                timeout=min(ATTEMPT_TIMEOUT_MAX, remaining),
                reply_to=reply_to,
            )
        except failures as exc:
            logger.warning("Provider %s failed: %s", provider.pk, type(exc).__name__)
            continue
        logger.info(
            "Contact message sent via provider %s to %d recipients", provider.pk, len(recipients)
        )
        return
    logger.error("All email providers failed after %d attempts", attempts)
    raise AllProvidersFailed(attempts)


def send_test_email(provider, to: str) -> None:
    """Single attempt with ``provider`` (active or not); exceptions propagate."""
    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    body = f"This is a test email sent via provider '{provider.name}' at {stamp}."
    _send_with(
        provider,
        subject=TEST_EMAIL_SUBJECT,
        body=body,
        to=[to],
        timeout=ATTEMPT_TIMEOUT_MAX,
    )
