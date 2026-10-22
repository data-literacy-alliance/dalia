"""Fernet helpers for stored email provider credentials.

The key is a 64-hex-character secret read once per process from
``settings.EMAIL_FERNET_KEY_FILE``. A missing or invalid key never raises at
import or request time; callers check ``key_status()`` or catch
``EncryptionKeyUnavailable``.
"""

import base64
import logging
import re
import threading

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.views.decorators.debug import sensitive_variables

from .exceptions import CredentialDecryptError, EncryptionKeyUnavailable

logger = logging.getLogger(__name__)

STATUS_OK = "ok"
STATUS_MISSING = "missing"
STATUS_INVALID = "invalid"

_HEX_KEY_RE = re.compile(r"^[0-9a-fA-F]{64}$")

_lock = threading.Lock()
_cache: tuple[Fernet | None, str] | None = None


def _reset_cache() -> None:
    """Forget the cached key (tests, key rotation in a long-lived process)."""
    global _cache
    with _lock:
        _cache = None


@sensitive_variables()
def _load() -> tuple[Fernet | None, str]:
    path = settings.EMAIL_FERNET_KEY_FILE
    try:
        with open(path, encoding="ascii") as handle:
            value = handle.read().strip()
    except (OSError, UnicodeDecodeError):
        logger.warning("Email encryption key file missing or unreadable: %s", path)
        return None, STATUS_MISSING
    if not value:
        logger.warning("Email encryption key file is empty: %s", path)
        return None, STATUS_MISSING
    if not _HEX_KEY_RE.match(value):
        logger.warning("Email encryption key file has an invalid format: %s", path)
        return None, STATUS_INVALID
    key = base64.urlsafe_b64encode(bytes.fromhex(value))
    return Fernet(key), STATUS_OK


@sensitive_variables()
def _state() -> tuple[Fernet | None, str]:
    global _cache
    with _lock:
        if _cache is None:
            _cache = _load()
        return _cache


@sensitive_variables()
def get_fernet() -> Fernet | None:
    """Return the process-wide Fernet instance, or None when no usable key exists."""
    return _state()[0]


def key_status() -> str:
    """Return ``"ok"``, ``"missing"`` or ``"invalid"``."""
    return _state()[1]


@sensitive_variables()
def encrypt(plaintext: str) -> str:
    fernet = get_fernet()
    if fernet is None:
        raise EncryptionKeyUnavailable("Email encryption key is " + key_status())
    return fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")


@sensitive_variables()
def decrypt(token: str) -> str:
    fernet = get_fernet()
    if fernet is None:
        raise EncryptionKeyUnavailable("Email encryption key is " + key_status())
    try:
        return fernet.decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeError):
        # Deliberately no chained exception: nothing from the payload in tracebacks.
        raise CredentialDecryptError("Stored credential cannot be decrypted") from None
