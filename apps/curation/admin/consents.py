"""
Admin classes for consent models (GDPR/legal compliance).
"""

from core.admin import BaseModelAdmin
from curation.models import ResourceConsent, ResourcePublishingConsent
from django.contrib import admin


@admin.register(ResourceConsent)
class ResourceConsentAdmin(BaseModelAdmin):
    list_display = (
        "person",
        "resource_content_title",
        "consent_type",
        "status",
        "granted_at",
        "uuid",
    )
    list_filter = ("consent_type", "status", "legal_basis", "granted_at")
    search_fields = (
        "resource_content__id",
        "resource_content__title",
        "resource_content__resource__id",
        "resource_content__resource__title",
        "person__first_name",
        "person__last_name",
        "uuid",
    )
    readonly_fields = (
        "uuid",
        "created",
        "modified",
        "granted_at",
        "withdrawn_at",
        "ip_address",
        "user_agent",
    )
    raw_id_fields = ("resource_content", "person")

    fieldsets = (
        (
            None,
            {
                "fields": ("resource_content", "person", "consent_type", "status", "uuid"),
            },
        ),
        (
            "Legal Details",
            {
                "fields": ("legal_basis", "consent_text", "consent_version"),
            },
        ),
        (
            "Timeline",
            {
                "fields": ("granted_at", "withdrawn_at", "expires_at"),
            },
        ),
        (
            "Technical",
            {
                "fields": ("ip_address", "user_agent", "withdrawal_reason"),
                "classes": ("collapse",),
            },
        ),
    )

    def resource_content_title(self, obj):
        return obj.resource_content.title[:50]

    resource_content_title.short_description = "Resource"

    @admin.action(description="Grant consent for selected items")
    def grant_consent(self, request, queryset):
        for consent in queryset.filter(status="pending"):
            consent.grant_consent(
                consent_text=consent.consent_text,
                version=consent.consent_version,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        self.message_user(
            request, f"Granted consent for {queryset.filter(status='pending').count()} items."
        )

    @admin.action(description="Withdraw consent for selected items")
    def withdraw_consent(self, request, queryset):
        for consent in queryset.filter(status="granted"):
            consent.withdraw_consent("Admin withdrawal")
        self.message_user(
            request, f"Withdrew consent for {queryset.filter(status='granted').count()} items."
        )

    actions = [grant_consent, withdraw_consent]

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(ResourcePublishingConsent)
class ResourcePublishingConsentAdmin(BaseModelAdmin):
    list_display = (
        "resource_content_title",
        "consenting_person",
        "cc0_agreed",
        "data_processing_agreed",
        "is_active",
        "created",
        "uuid",
    )
    list_filter = (
        "cc0_agreed",
        "data_processing_agreed",
        "public_display_agreed",
        "analytics_agreed",
        "is_active",
        "created",
    )
    search_fields = (
        "resource_content__id",
        "resource_content__title",
        "resource_content__resource__id",
        "resource_content__resource__title",
        "consenting_person__first_name",
        "consenting_person__last_name",
        "uuid",
    )
    readonly_fields = (
        "uuid",
        "created",
        "modified",
        "consent_given_at",
        "withdrawn_at",
        "ip_address",
        "user_agent",
    )
    raw_id_fields = ("resource_content", "consenting_person")

    fieldsets = (
        (
            None,
            {
                "fields": ("resource_content", "consenting_person", "is_active", "uuid"),
            },
        ),
        (
            "Consents",
            {
                "fields": (
                    "cc0_agreed",
                    "data_processing_agreed",
                    "public_display_agreed",
                    "analytics_agreed",
                ),
            },
        ),
        (
            "Legal Framework",
            {
                "fields": ("tos_version", "privacy_policy_version", "gdpr_lawful_basis"),
            },
        ),
        (
            "Data Retention",
            {
                "fields": ("data_retention_period", "can_withdraw", "withdrawal_instructions"),
            },
        ),
        (
            "Audit Trail",
            {
                "fields": (
                    "consent_given_at",
                    "ip_address",
                    "user_agent",
                    "withdrawn_at",
                    "withdrawal_reason",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def resource_content_title(self, obj):
        return obj.resource_content.title[:50]

    resource_content_title.short_description = "Resource"

    @admin.action(description="Withdraw all consents for selected items")
    def withdraw_all_consents(self, request, queryset):
        for consent in queryset.filter(is_active=True):
            consent.withdraw_all("Admin withdrawal")
        self.message_user(
            request, f"Withdrew all consents for {queryset.filter(is_active=True).count()} items."
        )

    actions = [withdraw_all_consents]

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
