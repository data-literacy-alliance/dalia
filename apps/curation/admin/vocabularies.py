"""
Admin classes for vocabulary models (controlled vocabularies).
"""

from core.admin import BaseModelAdmin
from curation.models import (
    Discipline,
    FileFormat,
    Language,
    LearningResourceType,
    License,
    MediaType,
    ProficiencyLevel,
    TargetGroup,
)
from django import forms
from django.contrib import admin
from django.utils.html import format_html


@admin.register(
    LearningResourceType,
    License,
    ProficiencyLevel,
    TargetGroup,
    FileFormat,
    MediaType,
)
class VocabAdmin(BaseModelAdmin):
    list_display = ("label", "slug", "uri", "is_active", "uuid")
    list_filter = ("is_active",)
    search_fields = ("label", "slug", "uri", "uuid")
    readonly_fields = ("uuid",)


@admin.register(Language)
class LanguageAdmin(VocabAdmin):
    search_fields = ("label", "slug", "uri", "uuid", "code", "native_name")


class DisciplineAdminForm(forms.ModelForm):
    """Custom form for Discipline with parent selection dropdown."""

    class Meta:
        model = Discipline
        fields = ["label", "slug", "uri", "parent_id", "parent_label", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        disciplines = Discipline.objects.filter(is_active=True).order_by("label")
        choices = [("", "--- Root Level ---")]

        for discipline in disciplines:
            if kwargs.get("instance") and discipline.pk == kwargs["instance"].pk:
                continue
            level = discipline.get_level()
            indent = "    " * level
            label = f"{indent}{discipline.label}"
            choices.append((discipline.pk, label))

        self.fields["parent_id"].choices = choices
        self.fields["parent_id"].widget.choices = choices

        if "parent_label" in self.fields:
            self.fields["parent_label"].widget.attrs["readonly"] = True
            self.fields["parent_label"].help_text = "Auto-populated from selected parent"

    def clean(self):
        cleaned_data = super().clean()
        parent_id = cleaned_data.get("parent_id")
        instance = getattr(self, "instance", None)

        if parent_id:
            cleaned_data["parent_label"] = parent_id.label
        else:
            cleaned_data["parent_label"] = ""

        if parent_id and instance and instance.pk:
            if parent_id.pk == instance.pk:
                raise forms.ValidationError("A discipline cannot be its own parent.")
            if instance in parent_id.get_descendants():
                raise forms.ValidationError("Cannot create circular reference in hierarchy.")

        return cleaned_data


@admin.register(Discipline)
class DisciplineAdmin(BaseModelAdmin):
    form = DisciplineAdminForm
    list_display = ("indented_label", "parent_label", "children_count", "slug", "is_active", "uuid")
    list_filter = ("is_active", "parent_id")
    search_fields = ("label", "slug", "uri", "uuid", "parent_label")
    readonly_fields = ("uuid", "parent_label")

    fieldsets = (
        (None, {
            "fields": ("label", "slug", "uri", "parent_id", "uuid", "is_active"),
        }),
        ("Auto-populated", {
            "fields": ("parent_label",),
            "classes": ("collapse",),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("parent_id")

    def indented_label(self, obj):
        level = obj.get_level()
        indent = "    " * level
        return format_html("{}{}", indent, obj.label)
    indented_label.short_description = "Label"
    indented_label.admin_order_field = "label"

    def children_count(self, obj):
        count = obj.get_children().count()
        if count > 0:
            return format_html("<strong>{}</strong>", count)
        return count
    children_count.short_description = "Children"

    @admin.action(description="Move selected disciplines to root level")
    def move_to_root(self, request, queryset):
        queryset.update(parent_id=None, parent_label="")
        self.message_user(request, f"Moved {queryset.count()} disciplines to root level.")

    @admin.action(description="Activate selected disciplines")
    def activate_disciplines(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"Activated {queryset.count()} disciplines.")

    @admin.action(description="Deactivate selected disciplines")
    def deactivate_disciplines(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {queryset.count()} disciplines.")

    actions = [move_to_root, activate_disciplines, deactivate_disciplines]
