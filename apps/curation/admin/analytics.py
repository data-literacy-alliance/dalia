"""
Admin classes for analytics models (ViewEvent, EditLog).
"""

from core.admin import BaseModelAdmin
from curation.models import EditLog, ViewEvent
from django.contrib import admin


@admin.register(ViewEvent)
class ViewEventAdmin(BaseModelAdmin):
    list_display = (
        "user_display",
        "content_object_display",
        "created",
        "duration_seconds",
        "ip_address",
    )
    list_filter = ("content_type", "created", "user")
    search_fields = ("user__username", "ip_address", "session_id")
    readonly_fields = (
        "created",
        "modified",
        "user",
        "content_type",
        "object_id",
        "session_id",
        "ip_address",
        "user_agent",
        "referrer",
        "duration_seconds",
        "resource_uuid",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def user_display(self, obj):
        return obj.user.username if obj.user else f"Anonymous ({obj.session_id})"

    user_display.short_description = "User"

    def content_object_display(self, obj):
        if obj.content_object:
            return f"{obj.content_type.name}: {obj.content_object}"
        if obj.resource_uuid:
            return f"Resource UUID: {obj.resource_uuid}"
        if obj.content_type:
            return f"{obj.content_type.name} (ID: {obj.object_id})"
        return "Unknown"

    content_object_display.short_description = "Content Object"


@admin.register(EditLog)
class EditLogAdmin(BaseModelAdmin):
    list_display = ("user", "content_object_display", "action", "created", "uuid")
    list_filter = ("action", "content_type", "created", "user")
    search_fields = ("user__username", "reason", "uuid")
    readonly_fields = (
        "uuid",
        "created",
        "modified",
        "user",
        "content_type",
        "object_id",
        "action",
        "changes",
        "reason",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def content_object_display(self, obj):
        if obj.content_object:
            return f"{obj.content_type.name}: {obj.content_object}"
        return f"{obj.content_type.name} (ID: {obj.object_id})"

    content_object_display.short_description = "Content Object"
