"""
Admin classes for interaction models (Bookmark, Like).
"""

from core.admin import BaseModelAdmin
from curation.models import Bookmark, Like
from django.contrib import admin


@admin.register(Bookmark)
class BookmarkAdmin(BaseModelAdmin):
    list_display = ("user", "content_object_display", "created", "is_private", "uuid")
    list_filter = ("is_private", "content_type", "created")
    search_fields = ("user__username", "notes", "uuid")
    readonly_fields = ("uuid", "content_type", "object_id", "created", "modified")

    def content_object_display(self, obj):
        if obj.content_object:
            return f"{obj.content_type.name}: {obj.content_object}"
        return f"{obj.content_type.name} (ID: {obj.object_id})"

    content_object_display.short_description = "Content Object"


@admin.register(Like)
class LikeAdmin(BaseModelAdmin):
    list_display = ("user", "content_object_display", "created", "uuid")
    list_filter = ("content_type", "created")
    search_fields = ("user__username", "uuid")
    readonly_fields = ("uuid", "content_type", "object_id", "created", "modified")

    def content_object_display(self, obj):
        if obj.content_object:
            return f"{obj.content_type.name}: {obj.content_object}"
        return f"{obj.content_type.name} (ID: {obj.object_id})"

    content_object_display.short_description = "Content Object"
