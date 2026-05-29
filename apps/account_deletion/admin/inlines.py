"""
Admin inline classes for account deletion app.
"""
from unfold.admin import TabularInline

from ..models import AccountDeletionItem, AccountDeletionLog


class AccountDeletionItemInline(TabularInline):
    """
    Inline admin for deletion items (content review).
    """
    model = AccountDeletionItem
    extra = 0
    can_delete = False
    fields = [
        'model_display',
        'content_summary',
        'action',
        'admin_notes',
        'reviewed_by',
        'reviewed_at',
        'processing_error',
    ]
    readonly_fields = [
        'model_display',
        'content_summary',
        'processing_error',
    ]

    def model_display(self, obj):
        """Display app.model format."""
        return f"{obj.app_label}.{obj.model_name}"
    model_display.short_description = "Model"

    def has_add_permission(self, request, obj=None):
        return False


class AccountDeletionLogInline(TabularInline):
    """
    Inline admin for audit logs (read-only).
    """
    model = AccountDeletionLog
    extra = 0
    can_delete = False
    fields = [
        'timestamp',
        'action',
        'performed_by_display',
        'ip_address',
    ]
    readonly_fields = fields

    def performed_by_display(self, obj):
        """Display performed_by username or 'System'."""
        return obj.performed_by.username if obj.performed_by else 'System'
    performed_by_display.short_description = "Performed By"

    def has_add_permission(self, request, obj=None):
        return False
