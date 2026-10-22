"""Contact form handler: availability, anti-spam, rate limits, single-sender lock, PRG redirect.

Only HMAC keys of the client address (``ip_key``/``subnet_key``) are used in cache keys and logs; names,
email addresses and message bodies are never logged.
"""

import logging

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.utils import timezone
from mailing.exceptions import AllProvidersFailed, MailingUnavailable
from mailing.service import send_contact_message, sending_status
from website.client_ip import client_ip, ip_key, subnet_key
from website.forms import ContactForm, read_ts

logger = logging.getLogger(__name__)

MIN_FILL_SECONDS = 3
SUBJECT_MAX_LENGTH = 200
SENDING_LOCK_KEY = "website:contact:sending"
SENDING_LOCK_SECONDS = 45
COUNTER_TTL_SECONDS = 2 * 60 * 60


def _hour_stamp() -> str:
    return timezone.now().strftime("%Y%m%d%H")


def _incr(key: str) -> int:
    """Atomically increment a counter that expires after the hour bucket is over."""
    cache.add(key, 0, COUNTER_TTL_SECONDS)
    try:
        return cache.incr(key)
    except ValueError:  # key expired between add and incr
        cache.add(key, 0, COUNTER_TTL_SECONDS)
        return cache.incr(key)


def _decr(key: str) -> None:
    try:
        cache.decr(key)
    except ValueError:
        pass


def _clean_subject(title: str) -> str:
    return str(title).replace("\r", "").replace("\n", "")[:SUBJECT_MAX_LENGTH]


def _build_body(form: ContactForm) -> str:
    data = form.cleaned_data
    return (
        f"Title: {form.title_label(data['title'])}\n"
        f"Name: {data['firstname']} {data['lastname']}\n"
        f"Email: {data['email']}\n"
        f"\n{data['message']}\n"
    )


def _success_response(page) -> HttpResponse:
    return HttpResponseRedirect(page.get_public_path() + "?sent=1#contact-section")


def _register_rejection(reason: str, ip_hash: str) -> None:
    """Count a rejected submission; log it only while the hourly rejected cap is not exceeded."""
    limit = settings.WEBSITE_CONTACT_REJECTED_LIMIT_PER_HOUR
    count = _incr(f"website:contact:rejected:{_hour_stamp()}")
    if count <= limit:
        logger.info("Contact submission rejected: reason=%s ip=%s", reason, ip_hash)
    elif count == limit + 1:
        logger.warning(
            "Contact rejected-submission cap of %s per hour reached; further rejections not logged",
            limit,
        )


def _check_time_trap(form: ContactForm) -> str | None:
    """Return the string key of the error message to show, or ``None`` when the token is fine."""
    age = read_ts(form.cleaned_data.get("ts", ""))
    if age is None:
        return "contact_token_invalid"
    if age < MIN_FILL_SECONDS:
        return "contact_too_fast"
    return None


def handle_contact(request: HttpRequest, page) -> tuple[ContactForm, HttpResponse | None, bool]:
    """Process the contact form of ``page``.

    Returns ``(form, response, contact_enabled)``; ``response`` is a redirect on success (or for a honeypot
    hit, indistinguishable from success) and ``None`` when the page should be rendered with ``form``.
    """
    lang = getattr(page, "language", "en") or "en"
    enabled = bool(sending_status().available)

    if request.method != "POST":
        return ContactForm(lang=lang), None, enabled

    form = ContactForm(request.POST, lang=lang)
    strings = form.strings
    ip = client_ip(request)
    ip_hash = ip_key(ip)

    if not enabled:
        logger.warning("Contact submission refused: sending unavailable ip=%s", ip_hash)
        form.add_error(None, strings["contact_unavailable"])
        return form, None, enabled

    if not form.is_valid():
        _register_rejection("invalid", ip_hash)
        return form, None, enabled

    if form.cleaned_data["website_url"]:
        _register_rejection("honeypot", ip_hash)
        return form, _success_response(page), enabled

    trap_error = _check_time_trap(form)
    if trap_error:
        _register_rejection(trap_error, ip_hash)
        form.add_error(None, strings[trap_error])
        return form, None, enabled

    hour = _hour_stamp()
    counters = (
        (f"website:contact:ip:{ip_hash}:{hour}", settings.WEBSITE_CONTACT_RATE_LIMIT_PER_HOUR),
        (
            f"website:contact:net:{subnet_key(ip)}:{hour}",
            settings.WEBSITE_CONTACT_SUBNET_LIMIT_PER_HOUR,
        ),
        (f"website:contact:all:{hour}", settings.WEBSITE_CONTACT_GLOBAL_LIMIT_PER_HOUR),
    )
    incremented = []
    for key, limit in counters:
        incremented.append(key)
        if _incr(key) > limit:
            logger.warning("Contact submission rate limited ip=%s", ip_hash)
            form.add_error(None, strings["contact_rate_limited"])
            return form, None, enabled

    if not cache.add(SENDING_LOCK_KEY, 1, SENDING_LOCK_SECONDS):
        for key in incremented:  # nothing was sent: do not burn the visitor's quota
            _decr(key)
        form.add_error(None, strings["contact_busy"])
        return form, None, enabled

    try:
        send_contact_message(
            subject=_clean_subject(getattr(page, "title", "")),
            body=_build_body(form),
            reply_to=form.cleaned_data["email"],
        )
    except MailingUnavailable as exc:
        logger.warning(
            "Contact message not sent: mailing unavailable reasons=%s", ",".join(exc.reasons)
        )
        form.add_error(None, strings["contact_unavailable"])
        return form, None, False
    except AllProvidersFailed as exc:
        logger.error(
            "Contact message not sent: all providers failed attempts=%s ip=%s",
            exc.attempts,
            ip_hash,
        )
        form.add_error(None, strings["contact_failed"])
        return form, None, enabled
    finally:
        cache.delete(SENDING_LOCK_KEY)

    return form, _success_response(page), enabled
