"""Contact form with honeypot and signed-timestamp time trap."""

import time

from django import forms
from django.conf import settings
from django.core.signing import BadSignature, TimestampSigner
from website.strings import get_strings

TITLE_VALUES = ("nA", "Herr", "Frau", "Dr", "Prof")
MESSAGE_MAX_LENGTH = 5000
NAME_MAX_LENGTH = 100
TS_MAX_AGE_SECONDS = 24 * 60 * 60


def _signer() -> TimestampSigner:
    return TimestampSigner(salt=settings.WEBSITE_CONTACT_SIGNER_SALT)


def make_ts() -> str:
    """Return a signed token carrying the current time."""
    return _signer().sign(str(int(time.time())))


def read_ts(value: str) -> int | None:
    """Return the age in seconds of a valid, unexpired token, else ``None``."""
    try:
        payload = _signer().unsign(value, max_age=TS_MAX_AGE_SECONDS)
        return max(int(time.time()) - int(payload), 0)
    except (BadSignature, ValueError, TypeError):
        return None


class _SingleLineCharField(forms.CharField):
    """CharField that rejects CR/LF (header safety)."""

    def __init__(self, *args, newline_message="", **kwargs):
        self._newline_message = newline_message
        super().__init__(*args, **kwargs)

    def validate(self, value):
        super().validate(value)
        if value and ("\r" in value or "\n" in value):
            raise forms.ValidationError(self._newline_message, code="newline")


class ContactForm(forms.Form):
    firstname = _SingleLineCharField(max_length=NAME_MAX_LENGTH)
    lastname = _SingleLineCharField(max_length=NAME_MAX_LENGTH)
    email = forms.EmailField(max_length=254)
    title = forms.ChoiceField(choices=[(v, v) for v in TITLE_VALUES])
    message = forms.CharField(max_length=MESSAGE_MAX_LENGTH, widget=forms.Textarea)
    website_url = forms.CharField(required=False, max_length=500)  # honeypot
    ts = forms.CharField(required=False, max_length=200)

    def __init__(self, *args, lang: str = "en", **kwargs):
        super().__init__(*args, **kwargs)
        self.lang = lang
        self.strings = get_strings(lang)
        strings = self.strings
        self.title_choices = [(v, strings[f"contact_title_{v}"]) for v in TITLE_VALUES]
        self.fields["title"].choices = self.title_choices
        for name in ("firstname", "lastname", "email", "title", "message"):
            messages = self.fields[name].error_messages
            messages["required"] = strings["contact_err_required"]
            if name == "email":
                messages["invalid"] = strings["contact_err_email"]
            if name == "title":
                messages["invalid_choice"] = strings["contact_err_choice"]
            max_length = getattr(self.fields[name], "max_length", None)
            if max_length:
                messages["max_length"] = strings["contact_err_max"] % {"max": max_length}
        for name in ("firstname", "lastname"):
            self.fields[name]._newline_message = strings["contact_err_newline"]

    def title_label(self, value: str) -> str:
        return dict(self.title_choices).get(value, "")

    @property
    def ts_value(self) -> str:
        """Token for the hidden field: keep a still-valid submitted one, otherwise issue a new one."""
        if self.is_bound:
            submitted = self.data.get("ts", "")
            if submitted and read_ts(submitted) is not None:
                return submitted
        return make_ts()
