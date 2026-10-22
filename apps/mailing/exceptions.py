"""Exceptions raised by the mailing app."""


class MailingError(Exception):
    """Base class for all mailing errors."""


class MailingUnavailable(MailingError):  # noqa: N818 (name fixed by contract)
    """Sending is not possible; ``reasons`` lists why (no_key, no_provider, no_recipient)."""

    def __init__(self, reasons: tuple[str, ...] = ()):
        self.reasons = tuple(reasons)
        super().__init__("Mailing unavailable")


class AllProvidersFailed(MailingError):  # noqa: N818 (name fixed by contract)
    """Every active provider failed; ``attempts`` is the number of providers tried."""

    def __init__(self, attempts: int):
        self.attempts = attempts
        super().__init__("All email providers failed")


class CredentialDecryptError(MailingError):
    """Stored provider credentials could not be decrypted."""


class EncryptionKeyUnavailable(MailingError):  # noqa: N818 (name fixed by contract)
    """The email encryption key is missing or invalid."""


class Smtp2goError(MailingError):
    """SMTP2GO API failure; message carries only status and error code."""

    def __init__(self, status: int | None = None, error_code: str | None = None):
        self.status = status
        self.error_code = error_code
        message = f"SMTP2GO HTTP {status}" if status is not None else "SMTP2GO error"
        if error_code:
            message = f"{message} {error_code}"
        super().__init__(message)


class UnsafeEndpointError(MailingError):
    """Provider endpoint resolves to a blocked address or violates endpoint rules."""
