"""Admin forms for the mailing app.

Secrets are write-only: the ciphertext model fields are never form fields, the
``*_new`` inputs never render a value, and the stored state is only described
("currently set" / "not set" / "must be re-entered").
"""

from django import forms
from django.core.exceptions import ValidationError
from unfold.widgets import UnfoldAdminEmailInputWidget, UnfoldAdminPasswordWidget

from . import connection_types, crypto
from .exceptions import CredentialDecryptError, EncryptionKeyUnavailable
from .models import ContactFormSettings, EmailProvider

KEY_UNAVAILABLE_MESSAGE = "Encryption key not available — credentials cannot be saved."
ENDPOINT_CHANGED_MESSAGE = "Connection settings changed — re-enter the credentials."
DUPLICATE_HELP = (
    "If a provider times out after it already accepted a message, the message "
    "may be delivered twice (the next provider is tried). Credentials are bound "
    "to the encryption key: replacing the key requires re-entering every secret."
)

# model ciphertext field -> (new-value form field, clear form field)
SECRET_FORM_FIELDS = {
    "password_enc": ("password_new", "clear_password"),
    "api_key_enc": ("api_key_new", "clear_api_key"),
    "secret_enc": ("secret_new", "clear_secret"),
}


def _secret_widget():
    return UnfoldAdminPasswordWidget(render_value=False, attrs={"autocomplete": "new-password"})


class EmailProviderForm(forms.ModelForm):
    password_new = forms.CharField(
        label="SMTP password", required=False, widget=_secret_widget(), strip=True
    )
    clear_password = forms.BooleanField(label="Remove stored SMTP password", required=False)
    api_key_new = forms.CharField(
        label="API key / token", required=False, widget=_secret_widget(), strip=True
    )
    clear_api_key = forms.BooleanField(label="Remove stored API key / token", required=False)
    secret_new = forms.CharField(
        label="Secret key", required=False, widget=_secret_widget(), strip=True
    )
    clear_secret = forms.BooleanField(label="Remove stored secret key", required=False)

    class Meta:
        model = EmailProvider
        fields = (
            "name",
            "connection_type",
            "host",
            "port",
            "security",
            "username",
            "api_url",
            "custom_endpoint",
            "sender_domain",
            "region",
            "project_id",
            "message_stream",
            "subaccount",
            "sandbox_id",
            "from_email",
            "from_name",
            "order",
            "is_active",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._secrets_applied = False
        self._plan: dict[str, tuple[str, bool]] = {}
        self.fields["custom_endpoint"].help_text = (
            "WARNING: lifts the host allowlist for API providers and the port allowlist for "
            "SMTP. The endpoint must still be https (API), free of credentials and must not "
            "resolve to a private address."
        )
        self.fields["is_active"].help_text = (
            "Active providers are tried in order. " + DUPLICATE_HELP
        )
        self.fields[
            "api_key_new"
        ].help_text = "API key, server token or API token (depending on the connection type)."
        for field, (new_name, _clear) in SECRET_FORM_FIELDS.items():
            state = self._stored_state(field)
            base = self.fields[new_name].help_text
            self.fields[new_name].help_text = f"{base} Currently: {state}.".strip()

    def _stored_state(self, field: str) -> str:
        """Describe a stored secret without ever exposing it."""
        instance = self.instance
        if instance.pk is None or not instance.has_secret(field):
            return "not set"
        try:
            instance.get_secret(field)
        except CredentialDecryptError:
            return "must be re-entered"
        except EncryptionKeyUnavailable:
            return "set (encryption key unavailable)"
        return "currently set"

    # --- validation ----------------------------------------------------------

    def _endpoint_changed(self, cleaned) -> bool:
        loaded = getattr(self.instance, "_loaded_endpoint", None)
        if self.instance.pk is None or loaded is None:
            return False
        return any(cleaned.get(f) != old for f, old in loaded.items() if f in cleaned)

    def clean(self):
        cleaned = super().clean()
        ctype = cleaned.get("connection_type")
        if ctype not in connection_types.CONNECTION_TYPES:
            return cleaned
        allowed = set(connection_types.allowed_fields(ctype))
        required = set(connection_types.required_fields(ctype))
        changed = self._endpoint_changed(cleaned)
        self._plan = {}
        entered_any = False

        for field, (new_name, clear_name) in SECRET_FORM_FIELDS.items():
            new_value = cleaned.get(new_name) or ""
            clear = bool(cleaned.get(clear_name))
            if new_value and clear:
                self.add_error(clear_name, "Enter a new value or remove the stored one, not both.")
                continue
            if new_value and field not in allowed:
                self.add_error(new_name, "This credential does not apply to this connection type.")
                continue
            if new_value:
                entered_any = True
            self._plan[field] = (new_value, clear)
            stored = self.instance.pk is not None and self.instance.has_secret(field)
            if changed and not new_value and not clear and (field in required or stored):
                self._add_endpoint_changed_error()
            elif field in required and not new_value and not (stored and not clear and not changed):
                self.add_error(new_name, "This credential is required for this connection type.")

        if entered_any and crypto.key_status() != crypto.STATUS_OK:
            self.add_error(None, KEY_UNAVAILABLE_MESSAGE)
        return cleaned

    def _add_endpoint_changed_error(self):
        if ENDPOINT_CHANGED_MESSAGE not in self.non_field_errors():
            self.add_error(None, ENDPOINT_CHANGED_MESSAGE)

    # --- persistence ---------------------------------------------------------

    def _apply_secrets(self):
        """Mirror the pending secret changes on the instance (idempotent)."""
        if self._secrets_applied:
            return
        self._secrets_applied = True
        instance = self.instance
        changed = self._endpoint_changed(self.cleaned_data)
        has_new = any(value for value, _clear in self._plan.values())
        if has_new and crypto.key_status() != crypto.STATUS_OK:
            return  # clean() already reported the error; nothing is saved
        for field, (new_value, clear) in self._plan.items():
            if new_value:
                instance.set_secret(field, new_value)
            elif clear or changed:
                instance.clear_secret(field)

    def _post_clean(self):
        # Secrets must be on the instance before the model validates its endpoint
        # rules, and before save() so the model keeps them when the endpoint changes.
        if hasattr(self, "cleaned_data") and not self.non_field_errors():
            self._apply_secrets()
        super()._post_clean()

    def save(self, commit=True):
        self._apply_secrets()
        return super().save(commit=commit)


class SendTestEmailForm(forms.Form):
    email = forms.EmailField(
        label="Send test email to", max_length=254, widget=UnfoldAdminEmailInputWidget
    )


class ContactFormSettingsForm(forms.ModelForm):
    class Meta:
        model = ContactFormSettings
        fields = ("recipients", "subject_prefix")
        widgets = {"recipients": forms.Textarea(attrs={"rows": 5})}

    def clean_recipients(self):
        value = self.cleaned_data["recipients"]
        if not ContactFormSettings._parse(value):
            raise ValidationError("Enter at least one recipient address.")
        return value
