"""
Admin for AccountDeletionLog model.
"""
from core.admin import BaseModelAdmin
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from ..models import AccountDeletionLog


@admin.register(AccountDeletionLog)
class AccountDeletionLogAdmin(BaseModelAdmin):
    """
    Admin interface for audit logs (read-only).
    """
    list_display = [
        'id',
        'timestamp',
        'deletion_request_link',
        'action',
        'performed_by_display',
        'ip_address',
    ]
    list_filter = [
        'action',
        'timestamp',
    ]
    search_fields = [
        'deletion_request__user__username',
        'action',
        'ip_address',
    ]
    readonly_fields = [
        'uuid',
        'deletion_request',
        'action',
        'details',
        'performed_by',
        'ip_address',
        'user_agent',
        'timestamp',
    ]
    fields = readonly_fields

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        # TESTING ONLY: Allow superuser deletion for testing/development
        # TODO: Change to 'return False' in production for GDPR compliance (7-year retention)
        return request.user.is_superuser

    def deletion_request_link(self, obj):
        """Link to parent deletion request."""
        url = reverse('admin:account_deletion_accountdeletionrequest_change', args=[obj.deletion_request.pk])
        return format_html('<a href="{}">Request #{}</a>', url, obj.deletion_request.id)
    deletion_request_link.short_description = "Deletion Request"

    def performed_by_display(self, obj):
        """Display username or System."""
        if obj.performed_by:
            url = reverse('admin:users_user_change', args=[obj.performed_by.id])
            return format_html('<a href="{}">{}</a>', url, obj.performed_by.username)
        return mark_safe('<em>System</em>')
    performed_by_display.short_description = "Performed By"
