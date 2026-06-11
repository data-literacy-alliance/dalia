"""
Admin for AccountDeletionItem model.
"""

from core.admin import BaseModelAdmin
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from ..models import AccountDeletionItem


@admin.register(AccountDeletionItem)
class AccountDeletionItemAdmin(BaseModelAdmin):
    """
    Admin interface for deletion items (content review).
    """

    list_display = [
        "id",
        "deletion_request_link",
        "model_display",
        "content_summary",
        "action_badge",
        "reviewed_by",
        "reviewed_at",
    ]
    list_filter = [
        "action",
        "app_label",
        "model_name",
        "reviewed_at",
    ]
    search_fields = [
        "deletion_request__user__username",
        "model_name",
        "content_summary",
    ]
    readonly_fields = [
        "uuid",
        "deletion_request",
        "content_type",
        "object_id",
        "model_name",
        "app_label",
        "content_summary",
        "content_data",
        "processed_at",
        "processing_error",
        "created",
        "modified",
    ]
    fields = [
        "uuid",
        "deletion_request",
        "model_name",
        "app_label",
        "content_summary",
        "content_data",
        "action",
        "admin_notes",
        "reviewed_by",
        "reviewed_at",
        "processed_at",
        "processing_error",
    ]

    def deletion_request_link(self, obj):
        """Link to parent deletion request."""
        url = reverse(
            "admin:account_deletion_accountdeletionrequest_change", args=[obj.deletion_request.pk]
        )
        return format_html('<a href="{}">Request #{}</a>', url, obj.deletion_request.id)

    deletion_request_link.short_description = "Deletion Request"

    def model_display(self, obj):
        """Display app.model."""
        return f"{obj.app_label}.{obj.model_name}"

    model_display.short_description = "Model"

    def action_badge(self, obj):
        """Display action with color."""
        colors = {
            "pending": "#FFA500",
            "delete": "#DC3545",
            "anonymize": "#FFC107",
            "keep": "#28A745",
        }
        color = colors.get(obj.action, "#000000")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; '
            'border-radius: 3px;">{}</span>',
            color,
            obj.get_action_display(),
        )

    action_badge.short_description = "Action"
