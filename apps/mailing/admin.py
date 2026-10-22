"""Mailing admin: superuser-only email providers, contact form settings, test email."""

from datetime import datetime

from core.admin import BaseModelAdmin
from django.conf import settings
from django.contrib import admin, messages
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from unfold.decorators import action

from . import crypto, service
from .connection_types import SECRET_FIELDS
from .forms import ContactFormSettingsForm, EmailProviderForm, SendTestEmailForm
from .models import ContactFormSettings, EmailProvider

DEFAULT_TEST_LIMIT_PER_HOUR = 10
TEST_RATE_WINDOW_SECONDS = 3600

KEY_BANNER = (
    "Email encryption key missing or invalid — sending disabled. Set it with "
    "`make secrets-edit NAME=dalia20_email_fernet_key` (64 hex chars, "
    "`openssl rand -hex 32`) and restart."
)

SENDING_REASON_TEXT = {
    "no_key": "encryption key missing or invalid",
    "no_provider": "no active provider with complete credentials",
    "no_recipient": "no recipient configured",
}

CREDENTIAL_BADGES = {
    "ok": ("ok", "#15803d"),
    "missing": ("not set", "#b45309"),
    "reenter": ("must be re-entered", "#b91c1c"),
}


class KeyBannerMixin:
    """Adds warning banners (GET only, so redirects do not repeat them)."""

    def _add_banners(self, request):
        if request.method != "GET":
            return
        if crypto.key_status() != crypto.STATUS_OK:
            messages.warning(request, KEY_BANNER)
        names = [
            p.name
            for p in EmailProvider.objects.filter(is_active=True)
            if p.credentials_status() == "reenter"
        ]
        if names:
            messages.warning(
                request,
                "Credentials must be re-entered for active provider(s): "
                + ", ".join(names)
                + ". They are skipped when sending until then.",
            )

    def changelist_view(self, request, extra_context=None):
        self._add_banners(request)
        return super().changelist_view(request, extra_context)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        self._add_banners(request)
        return super().changeform_view(request, object_id, form_url, extra_context)


def describe_send_error(exc: BaseException, provider: EmailProvider) -> str:
    """Class name plus numeric status codes only; never the exception message."""
    text = type(exc).__name__
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(exc, "status", None)
    if isinstance(status, int) and not isinstance(status, bool):
        text += f" (HTTP {status})"
    smtp_code = getattr(exc, "smtp_code", None)
    if isinstance(smtp_code, int) and not isinstance(smtp_code, bool):
        text += f" (SMTP {smtp_code})"
    # Defence in depth: never let a stored secret reach the message.
    for field in SECRET_FIELDS:
        try:
            secret = provider.get_secret(field)
        except Exception:  # noqa: BLE001 - undecryptable / no key: nothing to redact
            continue
        if secret:
            text = text.replace(secret, "***")
    return text


def _rate_limit_exceeded(user) -> bool:
    limit = getattr(settings, "MAILING_TEST_EMAIL_LIMIT_PER_HOUR", DEFAULT_TEST_LIMIT_PER_HOUR)
    key = f"mailing:test:{user.pk}:{datetime.now().strftime('%Y%m%d%H')}"
    cache.add(key, 0, TEST_RATE_WINDOW_SECONDS)
    try:
        count = cache.incr(key)
    except ValueError:  # expired between add and incr
        cache.set(key, 1, TEST_RATE_WINDOW_SECONDS)
        count = 1
    return count > limit


@admin.register(EmailProvider)
class EmailProviderAdmin(KeyBannerMixin, BaseModelAdmin):
    form = EmailProviderForm
    list_display = (
        "name",
        "connection_type",
        "from_email",
        "order",
        "is_active",
        "credentials_badge",
    )
    list_filter = ("connection_type", "is_active")
    ordering = ("order", "name")
    search_fields = ("name", "from_email")
    readonly_fields = ("created_at", "updated_at")
    actions_detail = ["send_test_email_link"]

    fieldsets = (
        (None, {"fields": ("name", "connection_type", "is_active", "order")}),
        (
            "Connection",
            {
                "fields": (
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
                ),
                "description": "Only the fields that apply to the connection type may be filled.",
            },
        ),
        (
            "Credentials (write-only)",
            {
                "fields": (
                    "password_new",
                    "clear_password",
                    "api_key_new",
                    "clear_api_key",
                    "secret_new",
                    "clear_secret",
                ),
                "description": (
                    "Stored values are never shown. Changing connection settings clears the "
                    "stored credentials; they must then be entered again."
                ),
            },
        ),
        ("Sender", {"fields": ("from_email", "from_name")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    # Superusers only: model permissions alone never suffice.
    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    @admin.display(description="Credentials")
    def credentials_badge(self, obj):
        label, color = CREDENTIAL_BADGES[obj.credentials_status()]
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; border-radius: 3px; '
            'color: white;">{}</span>',
            color,
            label,
        )

    @admin.action(description="Activate selected providers")
    def activate_providers(self, request, queryset):
        count = queryset.update(is_active=True)
        service.invalidate_sending_status()
        self.message_user(request, f"Activated {count} providers.")

    @admin.action(description="Deactivate selected providers")
    def deactivate_providers(self, request, queryset):
        count = queryset.update(is_active=False)
        service.invalidate_sending_status()
        self.message_user(request, f"Deactivated {count} providers.")

    actions = [activate_providers, deactivate_providers]

    @action(description="Send test email", permissions=["change"])
    def send_test_email_link(self, request, object_id):
        """Only navigates to the confirmation form; sending needs a POST there."""
        return redirect(reverse("admin:mailing_emailprovider_send_test", args=[object_id]))

    def get_urls(self):
        custom = [
            path(
                "<path:object_id>/send-test/",
                self.admin_site.admin_view(self.send_test_view),
                name="mailing_emailprovider_send_test",
            )
        ]
        return custom + super().get_urls()

    def send_test_view(self, request, object_id):
        if not request.user.is_superuser:
            raise PermissionDenied
        provider = get_object_or_404(self.get_queryset(request), pk=object_id)
        change_url = reverse("admin:mailing_emailprovider_change", args=[provider.pk])
        form = SendTestEmailForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            if _rate_limit_exceeded(request.user):
                messages.error(request, "Too many test emails this hour. Try again later.")
            else:
                self._send_test(request, provider, form.cleaned_data["email"])
            return HttpResponseRedirect(change_url)
        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": f"Send test email via {provider.name}",
            "provider": provider,
            "form": form,
            "change_url": change_url,
        }
        return TemplateResponse(request, "admin/mailing/emailprovider/send_test.html", context)

    def _send_test(self, request, provider, to):
        try:
            service.send_test_email(provider, to)
        except Exception as exc:  # noqa: BLE001 - every failure is reported, redacted
            messages.error(request, f"Test email failed: {describe_send_error(exc, provider)}")
        else:
            messages.success(request, f"Test email sent to {to} via {provider.name}.")


@admin.register(ContactFormSettings)
class ContactFormSettingsAdmin(KeyBannerMixin, BaseModelAdmin):
    form = ContactFormSettingsForm
    fields = ("recipients", "subject_prefix", "sending_status_display")
    readonly_fields = ("sending_status_display",)

    def has_add_permission(self, request):
        return super().has_add_permission(request) and not ContactFormSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Single record: go straight to it (banners are added by the change view).
        obj = ContactFormSettings.load()
        if obj is None:
            return redirect(reverse("admin:mailing_contactformsettings_add"))
        return redirect(reverse("admin:mailing_contactformsettings_change", args=[obj.pk]))

    @admin.display(description="Sending status")
    def sending_status_display(self, obj):
        status = service.sending_status()
        if status.available:
            return "Available"
        reasons = ", ".join(SENDING_REASON_TEXT.get(r, r) for r in status.reasons)
        return f"Unavailable: {reasons}"
