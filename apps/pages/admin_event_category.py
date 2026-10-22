"""EventCategory admin (pattern of curation RelationTypeCategoryAdmin)."""

from core.admin import BaseModelAdmin
from django.contrib import admin
from django.utils.html import format_html
from pages.models import EventCategory


@admin.register(EventCategory)
class EventCategoryAdmin(BaseModelAdmin):
    list_display = (
        "name_en",
        "name_de",
        "color_display",
        "events_count",
        "order",
        "is_active",
        "uuid",
    )
    list_filter = ("is_active",)
    search_fields = ("name_en", "name_de", "description", "uuid")
    readonly_fields = ("uuid", "created", "modified")
    ordering = ("order", "name_en")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name_en",
                    "name_de",
                    "description",
                    "color",
                    "order",
                    "is_active",
                    "uuid",
                ),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created", "modified"),
                "classes": ("collapse",),
            },
        ),
    )

    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; border-radius: 3px; color: white;">{}</span>',
            obj.color,
            obj.color,
        )

    color_display.short_description = "Color"

    def events_count(self, obj):
        count = obj.events.count()
        if count > 0:
            return format_html("<strong>{}</strong>", count)
        return count

    events_count.short_description = "Events"

    @admin.action(description="Activate selected categories")
    def activate_categories(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"Activated {count} categories.")

    @admin.action(description="Deactivate selected categories")
    def deactivate_categories(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {count} categories.")

    actions = [activate_categories, deactivate_categories]
