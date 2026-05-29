"""
Admin for SyncLog model.
"""
import json
from django.contrib import admin
from django.utils.html import format_html

from ..models import SyncLog

@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    """
    Admin interface for SyncLog with filtering and search.
    """

    list_display = [
        'id',
        'entity_mapping_link',
        'action_display',
        'status_display',
        'message_truncated',
        'created_by',
        'created'
    ]

    list_filter = [
        'action',
        'status',
        'created_by',
        'created'
    ]

    search_fields = [
        'message',
        'entity_mapping__fuseki_uri',
        'entity_mapping__postgresql_uuid',
        'details'
    ]

    readonly_fields = [
        'entity_mapping',
        'action',
        'status',
        'message',
        'details',
        'created',
        'created_by'
    ]

    date_hierarchy = 'created'

    def entity_mapping_link(self, obj):
        """Link to related entity mapping."""
        if obj.entity_mapping:
            url = reverse('admin:entity_mapping_entitymapping_change',
                         args=[obj.entity_mapping.id])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                f"{obj.entity_mapping.entity_type} #{obj.entity_mapping.id}"
            )
        return '-'
    entity_mapping_link.short_description = 'Entity Mapping'

    def action_display(self, obj):
        """Display action with icon."""
        icons = {
            'create_mapping': '➕',
            'update_mapping': '✏️',
            'sync_to_fuseki': '⬆️',
            'import_from_fuseki': '⬇️',
            'bulk_operation': '📦',
            'conflict_resolution': '⚖️'
        }
        icon = icons.get(obj.action, '❓')
        return format_html(
            '{} {}',
            icon,
            obj.get_action_display()
        )
    action_display.short_description = 'Action'

    def status_display(self, obj):
        """Display status with color coding."""
        colors = {
            'success': '#28a745',
            'error': '#dc3545',
            'warning': '#ffc107'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'

    def message_truncated(self, obj):
        """Display truncated message."""
        if len(obj.message) > 50:
            return f"{obj.message[:50]}..."
        return obj.message
    message_truncated.short_description = 'Message'

    def has_add_permission(self, request):
        """Disable manual log creation."""
        return False

    def has_change_permission(self, request, obj=None):
        """Disable log editing."""
        return False

