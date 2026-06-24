"""
Admin classes for resource models (Resource, ResourceContent).
"""

from urllib.parse import urlparse

from core.admin import BaseModelAdmin
from curation.admin.inlines import (
    ResourceCommunityRelationInline,
    ResourceLinkInline,
    ResourceRelatedItemInline,
)
from curation.models import Resource, ResourceContent
from django import forms
from unfold.widgets import UnfoldAdminSelectWidget, UnfoldAdminTextInputWidget
from django.contrib import admin
from django.db.models import Count, Min
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from taggit.forms import TagField
from taggit.utils import edit_string_for_tags
import difflib
from django.db import transaction
from django.http import Http404


@admin.register(Resource)
class ResourceAdmin(BaseModelAdmin):
    list_display = (
        "id",
        "title",
        "versions_count",
        "owner",
        "is_published",
        "published_at",
        "created",
        "is_removed",
        "uuid",
    )
    list_filter = ("is_removed", "is_published", "created")
    search_fields = ("id", "title", "owner__username", "uuid")
    actions = ("mark_as_removed", "unmark_removed", "merge_resources")
    readonly_fields = ("uuid", "versions_link")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            content_count=Count("contents", distinct=True),
            first_content_id=Min("contents__id"),
        )

    def content_link(self, obj):
        count = obj.content_count
        if count == 0:
            return mark_safe('<span style="color:#999;">—</span>')
        if count == 1:
            url = reverse("admin:curation_resourcecontent_change", args=[obj.first_content_id])
            return format_html(
                '<a href="{}" style="background:#0d6efd;color:#fff;padding:2px 8px;'
                'border-radius:3px;font-size:11px;text-decoration:none;white-space:nowrap;">'
                "Open Content</a>",
                url,
            )
        url = (
            reverse("admin:curation_resourcecontent_changelist") + f"?resource__id__exact={obj.pk}"
        )
        return format_html(
            '<a href="{}" style="background:#6c757d;color:#fff;padding:2px 8px;'
            'border-radius:3px;font-size:11px;text-decoration:none;white-space:nowrap;">'
            "{} Contents</a>",
            url,
            count,
        )

    content_link.short_description = "Content"
    content_link.admin_order_field = "content_count"

    def versions_count(self, obj):
        count = obj.content_count
        if count == 0:
            return mark_safe('<span style="color:#999;">0</span>')
        url = reverse("admin:curation_resource_versions", args=[obj.pk])
        return format_html(
            '<a href="{}" style="background:#7c3aed;color:#fff;padding:2px 10px;'
            'border-radius:3px;font-size:12px;font-weight:600;text-decoration:none;white-space:nowrap;">'
            "{}</a>",
            url,
            count,
        )

    versions_count.short_description = "Versions"
    versions_count.admin_order_field = "content_count"
    versions_count.allow_tags = True

    def versions_link(self, obj):
        if not obj.pk:
            return "—"
        url = reverse("admin:curation_resource_versions", args=[obj.pk])
        count = obj.contents.count()
        return format_html(
            '<a href="{}" style="background:#7c3aed;color:#fff;padding:4px 14px;'
            'border-radius:4px;font-size:12px;font-weight:500;text-decoration:none;display:inline-block;">'
            "View {} Version(s) ↗</a>",
            url,
            count,
        )

    versions_link.short_description = "Versions panel"

    def save_model(self, request, obj, form, change):
        if "is_published" in form.changed_data:
            obj.published_at = timezone.now() if obj.is_published else None
        super().save_model(request, obj, form, change)

    def get_urls(self):
        from django.urls import path

        urls = super().get_urls()
        custom = [
            path(
                "<int:pk>/versions/",
                self.admin_site.admin_view(self.versions_view),
                name="curation_resource_versions",
            ),
        ]
        return custom + urls

    def versions_view(self, request, pk):
        from django.shortcuts import render as django_render

        try:
            resource = Resource.objects.get(pk=pk)
        except Resource.DoesNotExist:
            raise Http404

        if not self.has_view_permission(request):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied

        contents = list(
            ResourceContent.objects.filter(resource=resource)
            .prefetch_related(
                "languages",
                "people",
                "organizations",
                "learning_resource_types",
                "disciplines",
                "licenses",
                "proficiency_levels",
                "target_groups",
                "file_formats",
                "media_types",
                "keywords",
            )
            .order_by("id")
        )

        SCALAR_FIELDS = [
            ("main_url", "Main URL"),
            ("description", "Description"),
            ("publication_date", "Publication date"),
            ("size_mb", "Size (MB)"),
        ]
        M2M_FIELDS = [
            ("languages", "Languages"),
            ("people", "People"),
            ("organizations", "Organizations"),
            ("learning_resource_types", "Learning resource types"),
            ("disciplines", "Disciplines"),
            ("licenses", "Licenses"),
            ("proficiency_levels", "Proficiency levels"),
            ("target_groups", "Target groups"),
            ("file_formats", "File formats"),
            ("media_types", "Media types"),
            ("keywords", "Keywords"),
        ]

        scalar_all = {
            name: [str(getattr(rc, name) or "") for rc in contents] for name, _ in SCALAR_FIELDS
        }
        m2m_all = {
            name: [set(str(x) for x in getattr(rc, name).all()) for rc in contents]
            for name, _ in M2M_FIELDS
        }

        def scalar_differs(vals):
            return len(set(vals)) > 1

        def m2m_field_differs(vals):
            if len(vals) <= 1:
                return False
            ref = vals[0]
            return any(v != ref for v in vals[1:])

        try:
            ref_idx = next(i for i, rc in enumerate(contents) if rc.is_active)
        except StopIteration:
            ref_idx = 0

        # Date/time fields excluded from consecutive-diff highlighting (trivially different)
        SKIP_CONSECUTIVE_DIFF = {"publication_date"}

        versions_data = []
        for i, rc in enumerate(contents):
            fields = []
            for name, label in SCALAR_FIELDS:
                curr_val = scalar_all[name][i]
                prev_val = scalar_all[name][i - 1] if i > 0 else None
                differs_from_prev = (
                    i > 0 and name not in SKIP_CONSECUTIVE_DIFF and curr_val != prev_val
                )
                fields.append(
                    {
                        "name": name,
                        "label": label,
                        "values": [curr_val],
                        "differs": scalar_differs(scalar_all[name]),
                        "differs_from_prev": differs_from_prev,
                    }
                )

            m2m_diffs = {}
            for name, label in M2M_FIELDS:
                my_set = m2m_all[name][i]
                ref_set = m2m_all[name][ref_idx]
                differs = m2m_field_differs(m2m_all[name])
                prev_set = m2m_all[name][i - 1] if i > 0 else set()
                differs_from_prev = i > 0 and my_set != prev_set
                if i != ref_idx and differs:
                    added = sorted(my_set - ref_set)
                    removed = sorted(ref_set - my_set)
                    unchanged = sorted(my_set & ref_set)
                    if added or removed:
                        m2m_diffs[name] = {"added": added, "removed": removed}
                    cell_values = unchanged
                else:
                    cell_values = sorted(my_set)
                fields.append(
                    {
                        "name": name,
                        "label": label,
                        "values": cell_values,
                        "differs": differs,
                        "differs_from_prev": differs_from_prev,
                    }
                )

            versions_data.append(
                {
                    "obj": rc,
                    "fields": fields,
                    "m2m_diffs": m2m_diffs,
                }
            )

        activate_url = reverse("admin:curation_resourcecontent_changelist")
        context = {
            **self.admin_site.each_context(request),
            "resource": resource,
            "versions": versions_data,
            "activate_url": activate_url,
            "title": f"Versions — {resource.title}",
            "opts": ResourceContent._meta,
        }
        return django_render(request, "admin/curation/resource/versions.html", context)

    @admin.action(
        description="Merge selected resources into one (published becomes canonical, else oldest)"
    )
    def merge_resources(self, request, queryset):
        if queryset.count() < 2:
            self.message_user(
                request,
                "Select at least 2 resources to merge.",
                level="error",
            )
            return

        resources = list(queryset.order_by("id"))

        # Prefer published resource as canonical; fall back to oldest (lowest id)
        published = [r for r in resources if r.is_published]
        canonical = published[0] if published else resources[0]
        to_merge = [r for r in resources if r.pk != canonical.pk]

        with transaction.atomic():
            # Carry published state to canonical if it came from a merged-away resource
            if not canonical.is_published and published:
                src = published[0]
                Resource.objects.filter(pk=canonical.pk).update(
                    is_published=True,
                    published_at=src.published_at,
                )

            for res in to_merge:
                ResourceContent.objects.filter(resource=res).update(
                    resource=canonical,
                    is_active=False,
                )

            # Recalculate version numbers for all RCs under canonical (ordered by id)
            all_rcs = list(ResourceContent.objects.filter(resource=canonical).order_by("id"))
            for idx, rc in enumerate(all_rcs, start=1):
                ResourceContent.objects.filter(pk=rc.pk).update(version=idx)

            # Ensure exactly one active RC: the original canonical's active RC wins;
            # if the canonical had none, activate its first RC
            active_exists = ResourceContent.objects.filter(
                resource=canonical, is_active=True
            ).exists()
            if not active_exists and all_rcs:
                ResourceContent.objects.filter(pk=all_rcs[0].pk).update(is_active=True)

            # Soft-delete the now-empty source resources (clear published flag first)
            Resource.objects.filter(pk__in=[r.pk for r in to_merge]).update(
                is_removed=True,
                is_published=False,
                published_at=None,
            )

            # When canonical is published, no RC should remain "pending review"
            canonical.refresh_from_db()
            if canonical.is_published:
                ResourceContent.objects.filter(resource=canonical).update(
                    submitted_for_review=False,
                    submitted_at=None,
                    submitted_by=None,
                )

        self.message_user(
            request,
            f"Merged {len(to_merge)} resource(s) into Resource #{canonical.pk} "
            f"({canonical.title!r}). {len(all_rcs)} version(s) total.",
        )

    @admin.action(description="Mark selected resources as removed (soft delete)")
    def mark_as_removed(self, request, queryset):
        queryset.update(is_removed=True)

    @admin.action(description="Unmark 'removed'")
    def unmark_removed(self, request, queryset):
        queryset.update(is_removed=False)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            actions.pop("delete_selected", None)
        return actions


class SelectResourceForm(forms.Form):
    resource = forms.ModelChoiceField(
        label=_("Resource"),
        queryset=Resource.objects.all().order_by("-id"),
        help_text=_("Pick the resource first, then continue to fill in the content."),
        widget=UnfoldAdminSelectWidget,
        required=True,
    )


class TaggitUnfoldWidget(UnfoldAdminTextInputWidget):
    """UnfoldAdminTextInputWidget that renders a taggit Tag queryset as comma-separated names."""

    def format_value(self, value):
        if value is not None and not isinstance(value, str):
            try:
                value = edit_string_for_tags(value)
            except (AttributeError, TypeError):
                pass
        return super().format_value(value)


class ResourceContentAdminForm(forms.ModelForm):
    keywords = TagField(
        label="Keywords",
        required=False,
        help_text="Comma-separated keywords, e.g. chemistry, FAIR data",
        widget=TaggitUnfoldWidget(attrs={"placeholder": "e.g. chemistry, FAIR data"}),
    )

    class Meta:
        model = ResourceContent
        fields = [
            "resource",
            "title",
            "main_url",
            "publication_date",
            "description",
            "size_mb",
            "created_by",
            "submitted_for_review",
            "submitted_at",
            "submitted_by",
            "languages",
            "people",
            "organizations",
            "learning_resource_types",
            "disciplines",
            "licenses",
            "proficiency_levels",
            "target_groups",
            "file_formats",
            "media_types",
            "keywords",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        deselect_hint = "Hold Ctrl (Windows/Linux) or Cmd (macOS) to toggle selection."
        for fname in (
            "people",
            "organizations",
            "learning_resource_types",
            "disciplines",
            "licenses",
            "proficiency_levels",
            "target_groups",
            "file_formats",
            "media_types",
            "languages",
        ):
            if fname in self.fields:
                self.fields[fname].help_text = deselect_hint

    def clean_keywords(self):
        tags = self.cleaned_data.get("keywords") or []
        return [t.lower().strip() for t in tags if t.strip()]

    def clean_main_url(self):
        """Normalize values like //example.com to https://example.com."""
        url = self.cleaned_data.get("main_url")
        if not url:
            return url
        p = urlparse(url)
        if not p.scheme:
            return "https://" + url.lstrip("/")
        return url

    def clean(self):
        cleaned = super().clean()
        languages = cleaned.get("languages")
        if not languages or languages.count() == 0:
            raise forms.ValidationError({"languages": "At least one language is required."})
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit and "keywords" in self.cleaned_data:
            kw = self.cleaned_data["keywords"]
            instance.keywords.set(*kw)
        return instance


@admin.register(ResourceContent)
class ResourceContentAdmin(BaseModelAdmin):
    form = ResourceContentAdminForm
    exclude = ("title",)

    list_display = (
        "resource_title",
        "version_link",
        "is_active",
        "resource",
        "get_languages",
        "created_by",
        "created",
        "review_flag",
        "uuid",
    )
    list_display_links = ("resource_title",)
    list_filter = ("is_active", "created_by", "submitted_for_review", "languages")
    search_fields = (
        "id",
        "title",
        "resource__id",
        "resource__title",
        "description",
        "main_url",
        "uuid",
    )
    inlines = (ResourceLinkInline, ResourceCommunityRelationInline, ResourceRelatedItemInline)

    filter_horizontal = (
        "people",
        "organizations",
        "learning_resource_types",
        "disciplines",
        "licenses",
        "proficiency_levels",
        "target_groups",
        "file_formats",
        "media_types",
        "languages",
    )

    readonly_fields = ("title", "resource_link", "uuid")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "resource",
                    "resource_link",
                    "uuid",
                    "languages",
                    "main_url",
                    "publication_date",
                    "description",
                    "size_mb",
                    "people",
                    "organizations",
                    "learning_resource_types",
                    "disciplines",
                    "licenses",
                    "proficiency_levels",
                    "target_groups",
                    "file_formats",
                    "media_types",
                    "keywords",
                    "created_by",
                    ("submitted_for_review", "submitted_at", "submitted_by"),
                ),
            },
        ),
    )

    def version_link(self, obj):
        url = reverse("admin:curation_resource_versions", args=[obj.resource_id])
        return format_html(
            '<a href="{}" style="background:#7c3aed;color:#fff;padding:2px 10px;'
            'border-radius:3px;font-size:12px;font-weight:600;text-decoration:none;white-space:nowrap;">'
            "v{}</a>",
            url,
            obj.version,
        )

    version_link.short_description = "Version"
    version_link.admin_order_field = "version"

    def resource_link(self, obj):
        if not obj.pk:
            return "\u2014"
        url = reverse("admin:curation_resource_change", args=[obj.resource_id])
        return format_html(
            '<a href="{}" target="_blank" style="background:#0d6efd;color:#fff;padding:4px 14px;'
            'border-radius:4px;font-size:12px;font-weight:500;text-decoration:none;display:inline-block;">'
            "Open Resource Admin ↗</a>",
            url,
        )

    resource_link.short_description = "Resource admin"

    def review_flag(self, obj):
        if obj.submitted_for_review:
            return mark_safe('<span style="color:#b45309;font-weight:500;">Needs review</span>')
        return mark_safe('<span style="color:#065f46;">\u2014</span>')

    review_flag.short_description = "Review"

    def get_languages(self, obj):
        if not obj.pk:
            return "\u2014"
        langs = obj.languages.all()
        if not langs:
            return "\u2014"
        return ", ".join([lang.code for lang in langs])

    get_languages.short_description = "Languages"

    @admin.display(description="Resource title", ordering="resource__title")
    def resource_title(self, obj):
        return obj.resource.title or "(untitled)"

    def has_delete_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)

    @admin.action(description="Set as active version (deactivates all siblings)")
    def set_active_version(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(
                request,
                "Please select exactly one version to activate.",
                level="error",
            )
            return
        target = queryset.first()
        resource_ids = set(queryset.values_list("resource_id", flat=True))
        if len(resource_ids) > 1:
            self.message_user(
                request,
                "All selected items must belong to the same resource.",
                level="error",
            )
            return
        with transaction.atomic():
            ResourceContent.objects.filter(
                resource_id=target.resource_id,
            ).exclude(pk=target.pk).update(is_active=False, submitted_for_review=False)
            ResourceContent.objects.filter(pk=target.pk).update(
                is_active=True,
                submitted_for_review=False,
            )
        self.message_user(
            request,
            f'Version {target.version} is now the active draft for "{target.resource}". '
            "Publish the resource via the Resource admin form to make it publicly visible.",
        )

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            actions.pop("delete_selected", None)
        return actions

    def get_urls(self):
        from django.urls import path

        urls = super().get_urls()
        custom = [
            path(
                "<int:pk>/activate/",
                self.admin_site.admin_view(self.activate_rc_view),
                name="curation_resourcecontent_activate",
            ),
        ]
        return custom + urls

    def activate_rc_view(self, request, pk):
        from django.http import JsonResponse

        if not self.has_change_permission(request):
            return JsonResponse({"ok": False, "error": "Permission denied"}, status=403)

        try:
            target = ResourceContent.objects.get(pk=pk)
        except ResourceContent.DoesNotExist:
            return JsonResponse({"ok": False, "error": "Not found"}, status=404)

        with transaction.atomic():
            ResourceContent.objects.filter(resource_id=target.resource_id).exclude(pk=pk).update(
                is_active=False, submitted_for_review=False
            )
            ResourceContent.objects.filter(pk=pk).update(is_active=True, submitted_for_review=False)

        return JsonResponse({"ok": True})

    def add_view(self, request, form_url="", extra_context=None):
        """
        Two-step add: step 1 selects a Resource, step 2 fills in content.
        """
        from django.shortcuts import render as django_render

        resource_id = request.GET.get("resource")

        if not resource_id:
            if request.method == "POST":
                form = SelectResourceForm(request.POST)
                if form.is_valid():
                    selected_resource = form.cleaned_data["resource"]
                    add_url = reverse("admin:curation_resourcecontent_add")
                    return redirect(f"{add_url}?resource={selected_resource.pk}")
            else:
                form = SelectResourceForm()

            context = {
                **self.admin_site.each_context(request),
                "opts": self.model._meta,
                "form": form,
                "title": _("Select resource"),
            }
            return django_render(
                request,
                "admin/curation/resourcecontent/select_resource_step.html",
                context,
            )

        return super().add_view(request, form_url, extra_context)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        resource_id = request.GET.get("resource")
        if resource_id:
            initial["resource"] = resource_id
            try:
                res = Resource.objects.only("id", "title").get(pk=resource_id)
                initial["title"] = res.title or ""
            except Resource.DoesNotExist:
                pass
        return initial

    def save_model(self, request, obj, form, change):
        """Keep ResourceContent.title in sync with Resource.title."""
        if obj.resource_id and obj.resource.title:
            obj.title = obj.resource.title
        if "submitted_for_review" in form.changed_data:
            if obj.submitted_for_review:
                obj.submitted_at = timezone.now()
                obj.submitted_by = request.user
            else:
                obj.submitted_at = None
        super().save_model(request, obj, form, change)
