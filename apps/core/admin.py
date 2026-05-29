"""
Core admin configuration.
Base admin classes for all DALIA 2.0 models.
"""

from django.contrib import admin, messages
from django.contrib.auth.models import Group
from import_export.admin import ImportExportModelAdmin as BaseImportExportModelAdmin
from unfold.admin import ModelAdmin as UnfoldModelAdmin


class BaseModelAdmin(UnfoldModelAdmin):
    """
    Base admin class for all DALIA 2.0 models.
    Provides Unfold theme integration and common configuration.

    Usage:
        class MyModelAdmin(BaseModelAdmin):
            list_display = ["field1", "field2"]
    """

    show_full_result_count = True
    list_per_page = 50
    date_hierarchy = None
    compressed_fields = True
    warn_unsaved_form = True


class ImportExportModelAdmin(BaseImportExportModelAdmin, UnfoldModelAdmin):
    """
    Base admin class for models that support import/export.
    Combines django-import-export with Unfold theme.
    """

    show_full_result_count = True
    list_per_page = 50
    compressed_fields = True
    warn_unsaved_form = True


# -- Group admin (User admin is in users/admin.py) -----------------------------

admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(UnfoldModelAdmin):
    """Django Group admin with Unfold theme."""

    search_fields = ("name",)


# -- Third-party app overrides (Unfold styling) --------------------------------
# Unregister plain ModelAdmin registrations from third-party packages and
# re-register them with UnfoldModelAdmin so every admin page is styled
# consistently with the Unfold theme.

from django import forms as _forms  # noqa: E402
from allauth.account.admin import EmailAddressAdmin as _EmailAddressAdmin  # noqa: E402
from allauth.account.models import EmailAddress  # noqa: E402
from allauth.socialaccount import providers as _allauth_providers  # noqa: E402
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken  # noqa: E402
from axes.admin import AccessAttemptAdmin as _AccessAttemptAdmin  # noqa: E402
from axes.admin import AccessFailureLogAdmin as _AccessFailureLogAdmin  # noqa: E402
from axes.admin import AccessLogAdmin as _AccessLogAdmin  # noqa: E402
from axes.models import AccessAttempt, AccessFailureLog, AccessLog  # noqa: E402
from django.contrib.sites.admin import SiteAdmin as _SiteAdmin  # noqa: E402
from django.contrib.sites.models import Site  # noqa: E402
from django_otp.plugins.otp_static.admin import StaticDeviceAdmin as _StaticDeviceAdmin  # noqa: E402
from django_otp.plugins.otp_static.models import StaticDevice  # noqa: E402
from django_otp.plugins.otp_totp.admin import TOTPDeviceAdmin as _TOTPDeviceAdmin  # noqa: E402
from django_otp.plugins.otp_totp.models import TOTPDevice  # noqa: E402
from rest_framework.authtoken.admin import TokenAdmin as _TokenAdmin  # noqa: E402
from rest_framework.authtoken.models import TokenProxy  # noqa: E402
from rest_framework_simplejwt.token_blacklist.admin import BlacklistedTokenAdmin as _BlacklistedTokenAdmin  # noqa: E402
from rest_framework_simplejwt.token_blacklist.admin import OutstandingTokenAdmin as _OutstandingTokenAdmin  # noqa: E402
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken  # noqa: E402
from taggit.admin import TagAdmin as _TagAdmin  # noqa: E402
from taggit.models import Tag  # noqa: E402

# Simple re-registrations: swap plain ModelAdmin for UnfoldModelAdmin.
# Use this for third-party models whose admin has no raw_id_fields,
# filter_horizontal, or custom form widgets that bypass Unfold styling.
_THIRD_PARTY = [
    (EmailAddress, _EmailAddressAdmin),
    (AccessAttempt, _AccessAttemptAdmin),
    (AccessFailureLog, _AccessFailureLogAdmin),
    (AccessLog, _AccessLogAdmin),
    (Site, _SiteAdmin),
    (StaticDevice, _StaticDeviceAdmin),
    (TOTPDevice, _TOTPDeviceAdmin),
    (TokenProxy, _TokenAdmin),
    (BlacklistedToken, _BlacklistedTokenAdmin),
    (OutstandingToken, _OutstandingTokenAdmin),
    (Tag, _TagAdmin),
]

for _model, _base in _THIRD_PARTY:
    try:
        admin.site.unregister(_model)
        admin.site.register(
            _model,
            type(f"Unfold{_base.__name__}", (UnfoldModelAdmin, _base), {}),
        )
    except admin.sites.NotRegistered:
        pass


# -- allauth socialaccount: explicit classes ----------------------------------
# The generic type() swap is not enough here because the original admin classes
# use raw_id_fields, filter_horizontal, and a custom form with explicit widget
# overrides — all of which bypass Unfold field styling.
# Fix: explicit classes with autocomplete_fields + a clean form.


class _SocialAppFormUnfold(_forms.ModelForm):
    """SocialApp form without explicit TextInput widget overrides.

    Keeps the dynamic provider ChoiceField populated from registered
    allauth providers, but drops the TextInput size attrs so Unfold
    can apply its own field styling.
    """

    class Meta:
        model = SocialApp
        exclude: list = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["provider"] = _forms.ChoiceField(
            choices=_allauth_providers.registry.as_choices()
        )


admin.site.unregister(SocialApp)


@admin.register(SocialApp)
class UnfoldSocialAppAdmin(BaseModelAdmin):
    form = _SocialAppFormUnfold
    list_display = ("name", "provider")
    list_filter = ("provider",)
    search_fields = ("name",)
    autocomplete_fields = ("sites",)  # replaces filter_horizontal


admin.site.unregister(SocialAccount)


@admin.register(SocialAccount)
class UnfoldSocialAccountAdmin(BaseModelAdmin):
    list_display = ("user", "uid", "provider")
    list_filter = ("provider",)
    search_fields = ("uid",)
    autocomplete_fields = ("user",)  # replaces raw_id_fields

    def get_search_fields(self, request):
        from allauth.account.adapter import get_adapter
        user_fields = get_adapter().get_user_search_fields()
        return list(self.search_fields) + [f"user__{f}" for f in user_fields]


admin.site.unregister(SocialToken)


@admin.register(SocialToken)
class UnfoldSocialTokenAdmin(BaseModelAdmin):
    list_display = ("app", "account", "expires_at")
    list_filter = ("app", "app__provider", "expires_at")
    search_fields = ("account__uid",)
    autocomplete_fields = ("app", "account")  # replaces raw_id_fields
