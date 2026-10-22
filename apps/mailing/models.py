"""Mailing models: outgoing email providers and contact form settings."""

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import models
from django.views.decorators.debug import sensitive_variables

from . import connection_types, crypto
from .exceptions import CredentialDecryptError, EncryptionKeyUnavailable

SECRET_FIELDS = connection_types.SECRET_FIELDS
MAX_RECIPIENTS = 20


def _secret_field(field: str) -> str:
    """Normalise ``password`` / ``password_enc`` to the model field name."""
    name = field if field.endswith("_enc") else f"{field}_enc"
    if name not in SECRET_FIELDS:
        raise ValueError(f"Unknown secret field: {field!r}")
    return name


class EmailProvider(models.Model):
    SECURITY_STARTTLS = "starttls"
    SECURITY_SSL = "ssl"
    SECURITY_NONE = "none"
    SECURITY_CHOICES = [
        (SECURITY_STARTTLS, "STARTTLS"),
        (SECURITY_SSL, "SSL/TLS"),
        (SECURITY_NONE, "None"),
    ]

    name = models.CharField(max_length=100, unique=True)
    connection_type = models.CharField(
        max_length=30, choices=connection_types.CONNECTION_TYPE_CHOICES
    )
    host = models.CharField(max_length=255, blank=True)
    port = models.PositiveIntegerField(null=True, blank=True)
    security = models.CharField(max_length=10, choices=SECURITY_CHOICES, default=SECURITY_STARTTLS)
    username = models.CharField(max_length=255, blank=True)
    password_enc = models.TextField(blank=True, editable=False)
    api_key_enc = models.TextField(blank=True, editable=False)
    secret_enc = models.TextField(blank=True, editable=False)
    sender_domain = models.CharField(max_length=255, blank=True)
    region = models.CharField(max_length=255, blank=True)
    project_id = models.CharField(max_length=255, blank=True)
    message_stream = models.CharField(max_length=255, blank=True)
    subaccount = models.CharField(max_length=255, blank=True)
    sandbox_id = models.CharField(max_length=255, blank=True)
    api_url = models.URLField(max_length=500, blank=True)
    custom_endpoint = models.BooleanField(default=False)
    from_email = models.EmailField()
    from_name = models.CharField(max_length=100, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "pk")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._loaded_endpoint = None
        self._secrets_set = set()

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<EmailProvider pk={self.pk} name={self.name!r} type={self.connection_type!r}>"

    def save(self, *args, **kwargs):
        cleared = []
        if self._endpoint_changed():
            for field in SECRET_FIELDS:
                if field not in self._secrets_set and getattr(self, field):
                    setattr(self, field, "")
                    cleared.append(field)
        update_fields = kwargs.get("update_fields")
        if cleared and update_fields is not None:
            kwargs["update_fields"] = list(set(update_fields) | set(cleared))
        super().save(*args, **kwargs)
        self._snapshot_endpoint()

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._snapshot_endpoint()
        return instance

    def refresh_from_db(self, *args, **kwargs):
        super().refresh_from_db(*args, **kwargs)
        self._snapshot_endpoint()

    def _snapshot_endpoint(self):
        fields = connection_types.ENDPOINT_FIELDS
        if all(f in self.__dict__ for f in fields):  # deferred fields: no tracking
            self._loaded_endpoint = {f: self.__dict__[f] for f in fields}
        else:
            self._loaded_endpoint = None
        self._secrets_set = set()

    # --- secrets -------------------------------------------------------------

    @sensitive_variables()
    def set_secret(self, field: str, value: str) -> None:
        name = _secret_field(field)
        if not value:
            self.clear_secret(name)
            return
        setattr(self, name, crypto.encrypt(value))
        self._secrets_set.add(name)

    def clear_secret(self, field: str) -> None:
        name = _secret_field(field)
        setattr(self, name, "")
        self._secrets_set.discard(name)

    def has_secret(self, field: str) -> bool:
        return bool(getattr(self, _secret_field(field)))

    @sensitive_variables()
    def get_secret(self, field: str) -> str:
        token = getattr(self, _secret_field(field))
        if not token:
            return ""
        return crypto.decrypt(token)

    def credentials_status(self) -> str:
        """``"ok"``, ``"missing"`` (incomplete or no key) or ``"reenter"`` (undecryptable)."""
        if self.connection_type not in connection_types.CONNECTION_TYPES:
            return "missing"
        for field in connection_types.required_fields(self.connection_type):
            if field in SECRET_FIELDS:
                if not self.has_secret(field):
                    return "missing"
            elif getattr(self, field) in (None, ""):
                return "missing"
        for field in SECRET_FIELDS:
            if not self.has_secret(field):
                continue
            try:
                self.get_secret(field)
            except EncryptionKeyUnavailable:
                return "missing"
            except CredentialDecryptError:
                return "reenter"
        return "ok"

    # --- validation / persistence ---------------------------------------------

    def clean(self):
        super().clean()
        if self.connection_type in connection_types.CONNECTION_TYPES:
            connection_types.validate_endpoint(self)

    def _endpoint_changed(self) -> bool:
        if self.pk is None or self._loaded_endpoint is None:
            return False
        return any(getattr(self, f) != old for f, old in self._loaded_endpoint.items())


class ContactFormSettings(models.Model):
    SINGLETON_KEY = "default"

    singleton_key = models.CharField(
        max_length=10, default=SINGLETON_KEY, unique=True, editable=False
    )
    recipients = models.TextField(help_text="One email address per line.")
    subject_prefix = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "contact form settings"
        verbose_name_plural = "contact form settings"

    def __str__(self):
        return "Contact form settings"

    @staticmethod
    def _parse(raw: str) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for line in (raw or "").splitlines():
            address = line.strip()
            if address and address.lower() not in seen:
                seen.add(address.lower())
                result.append(address)
        return result

    def clean(self):
        super().clean()
        addresses = self._parse(self.recipients)
        for address in addresses:
            try:
                validate_email(address)
            except ValidationError:
                raise ValidationError({"recipients": f"Invalid email address: {address}"}) from None
        if len(addresses) > MAX_RECIPIENTS:
            raise ValidationError(
                {"recipients": f"At most {MAX_RECIPIENTS} recipients are allowed."}
            )
        self.recipients = "\n".join(addresses)

    @classmethod
    def load(cls):
        return cls.objects.filter(singleton_key=cls.SINGLETON_KEY).first()

    def recipient_list(self) -> list[str]:
        return self._parse(self.recipients)
