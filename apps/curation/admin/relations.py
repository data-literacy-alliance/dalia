"""
Admin classes for relationship models (RelationTypeCategory, RelationType).
"""

import re

from core.admin import BaseModelAdmin
from curation.models import RelationType, RelationTypeCategory
from django import forms
from django.contrib import admin
from django.forms.widgets import Textarea
from django.utils.html import format_html, mark_safe


@admin.register(RelationTypeCategory)
class RelationTypeCategoryAdmin(BaseModelAdmin):
    list_display = ("name", "color_display", "relation_types_count", "order", "is_active", "uuid")
    list_filter = ("is_active",)
    search_fields = ("name", "description", "uuid")
    readonly_fields = ("uuid", "created", "modified")
    ordering = ("order", "name")

    fieldsets = (
        (
            None,
            {
                "fields": ("name", "description", "color", "order", "is_active", "uuid"),
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

    def relation_types_count(self, obj):
        count = obj.relation_types.filter(is_active=True).count()
        if count > 0:
            return format_html("<strong>{}</strong>", count)
        return count

    relation_types_count.short_description = "Active Types"

    @admin.action(description="Activate selected categories")
    def activate_categories(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"Activated {queryset.count()} categories.")

    @admin.action(description="Deactivate selected categories")
    def deactivate_categories(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {queryset.count()} categories.")

    actions = [activate_categories, deactivate_categories]


class RelationTypeForm(forms.ModelForm):
    """Custom form for RelationType with enhanced widgets."""

    class Meta:
        model = RelationType
        fields = ["code", "label", "description", "category", "order", "is_active"]
        widgets = {
            "description": Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = RelationTypeCategory.objects.filter(
            is_active=True
        ).order_by("order", "name")

    def clean_code(self):
        """Ensure code is a valid identifier."""
        code = self.cleaned_data.get("code")
        if code and not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", code):
            raise forms.ValidationError(
                "Code must start with a letter and contain only letters, numbers, and underscores."
            )
        return code


@admin.register(RelationType)
class RelationTypeAdmin(BaseModelAdmin):
    form = RelationTypeForm
    list_display = ("label", "code", "category_display", "order", "is_active", "uuid")
    list_filter = ("is_active", "category")
    search_fields = ("label", "code", "description", "uuid")
    readonly_fields = ("uuid", "created", "modified")
    ordering = ("category__order", "order", "label")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "code",
                    "label",
                    "description",
                    "category",
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

    def category_display(self, obj):
        if not obj.category:
            return mark_safe('<span style="color: #999;">—</span>')
        return format_html(
            '<span style="background-color: {}; padding: 1px 6px; border-radius: 3px; color: white; font-size: 0.8em;">{}</span>',
            obj.category.color,
            obj.category.name,
        )

    category_display.short_description = "Category"

    @admin.action(description="Activate selected relation types")
    def activate_types(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"Activated {queryset.count()} relation types.")

    @admin.action(description="Deactivate selected relation types")
    def deactivate_types(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {queryset.count()} relation types.")

    @admin.action(description="Create default relation type categories")
    def create_default_categories(self, request, queryset):
        default_categories = [
            {
                "name": "Content Relations",
                "description": "Relations describing content structure",
                "color": "#3b82f6",
                "order": 1,
            },
            {
                "name": "Version Relations",
                "description": "Relations describing version history",
                "color": "#10b981",
                "order": 2,
            },
            {
                "name": "Reference Relations",
                "description": "Relations describing citations and references",
                "color": "#f59e0b",
                "order": 3,
            },
            {
                "name": "Supplement Relations",
                "description": "Relations describing supplementary content",
                "color": "#8b5cf6",
                "order": 4,
            },
            {
                "name": "Translation Relations",
                "description": "Relations describing translations",
                "color": "#ef4444",
                "order": 5,
            },
        ]
        created_count = 0
        for cat in default_categories:
            if not RelationTypeCategory.objects.filter(name=cat["name"]).exists():
                RelationTypeCategory.objects.create(**cat)
                created_count += 1
        self.message_user(request, f"Created {created_count} default relation type categories.")

    actions = [activate_types, deactivate_types, create_default_categories]
