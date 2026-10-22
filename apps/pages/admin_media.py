"""Image library admin."""

from core.admin import BaseModelAdmin
from django.contrib import admin, messages
from django.contrib.admin.actions import delete_selected
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html, format_html_join
from pages.media_usage import find_usages, is_in_use, usage_counts
from pages.models import MediaImage, Page

UPLOAD_HELP = (
    "Images are stored without metadata (re-encoded). File names are predictable — "
    "do not upload confidential images before the page is published."
)
_COPY_BUTTON = (
    '<input type="text" readonly value="{}" size="70" style="max-width:100%"> '
    '<button type="button" class="button" '
    'onclick="navigator.clipboard.writeText(this.previousElementSibling.value)">Copy</button>'
)
_PAGE_ADMIN_NAMES = {
    Page.SITE_WEBSITE: "admin:pages_websitepage_change",
    Page.SITE_SEARCH: "admin:pages_searchpage_change",
}


def _page_admin_url(page: Page) -> str:
    for name in (_PAGE_ADMIN_NAMES.get(page.site), "admin:pages_page_change"):
        if not name:
            continue
        try:
            return reverse(name, args=[page.pk])
        except NoReverseMatch:
            continue
    return ""


@admin.register(MediaImage)
class MediaImageAdmin(BaseModelAdmin):
    list_display = (
        "thumbnail",
        "title",
        "file_name",
        "first_used_on",
        "uploaded_at",
        "uploaded_by",
        "used_on_count",
    )
    search_fields = ("title", "image")
    list_select_related = ("first_used_on", "uploaded_by")

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return [
                (
                    None,
                    {
                        "fields": ("image", "title", "alt_en", "alt_de", "first_used_on"),
                        "description": UPLOAD_HELP,
                    },
                )
            ]
        return [
            (
                None,
                {
                    "fields": ("image", "title", "alt_en", "alt_de", "first_used_on"),
                    "description": UPLOAD_HELP,
                },
            ),
            ("Usage", {"fields": ("used_on", "markdown_snippet_en", "markdown_snippet_de")}),
            ("Details", {"fields": ("sha256", "uploaded_at", "uploaded_by")}),
        ]

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ()
        return (
            "image",
            "used_on",
            "markdown_snippet_en",
            "markdown_snippet_de",
            "sha256",
            "uploaded_at",
            "uploaded_by",
        )

    # -- list columns -------------------------------------------------------
    @admin.display(description="Preview")
    def thumbnail(self, obj):
        if not obj.image:
            return ""
        return format_html('<img src="{}" style="max-height:60px" alt="">', obj.image.url)

    @admin.display(description="File name", ordering="image")
    def file_name(self, obj):
        return obj.image.name.rsplit("/", 1)[-1] if obj.image else ""

    @admin.display(description="Used on")
    def used_on_count(self, obj):
        count = getattr(obj, "_usage_count", None)
        return len(find_usages(obj)) if count is None else count

    def get_changelist_instance(self, request):
        changelist = super().get_changelist_instance(request)
        # One batch of queries for the whole page of results instead of one per row.
        changelist.result_list = list(changelist.result_list)
        counts = usage_counts(changelist.result_list)
        for image in changelist.result_list:
            image._usage_count = counts.get(image.pk, 0)
        return changelist

    # -- change form read-only fields ----------------------------------------
    @admin.display(description="Used on")
    def used_on(self, obj):
        pages = find_usages(obj)
        if not pages:
            return "Not used yet."
        return format_html(
            "<ul>{}</ul>",
            format_html_join(
                "",
                '<li><a href="{}">{}</a> ({}, {})</li>',
                ((_page_admin_url(p), p.title or p.slug, p.site, p.language) for p in pages),
            ),
        )

    def _snippet(self, obj, lang):
        if not obj.image:
            return ""
        return format_html(_COPY_BUTTON, obj.markdown_snippet(lang))

    @admin.display(description="Markdown snippet (EN)")
    def markdown_snippet_en(self, obj):
        return self._snippet(obj, "en")

    @admin.display(description="Markdown snippet (DE)")
    def markdown_snippet_de(self, obj):
        return self._snippet(obj, "de")

    # -- behaviour -------------------------------------------------------------
    def save_model(self, request, obj, form, change):
        if not change:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        allowed = super().has_delete_permission(request, obj)
        return allowed and (obj is None or not is_in_use(obj))

    def change_view(self, request, object_id, form_url="", extra_context=None):
        if request.method == "GET":
            obj = self.get_object(request, object_id)
            if obj is not None and is_in_use(obj):
                messages.warning(
                    request,
                    "This image is in use and cannot be deleted. Remove it from the pages "
                    "listed under 'Used on' first.",
                )
        return super().change_view(request, object_id, form_url, extra_context)

    def _in_use_titles(self, queryset):
        return [str(img) for img in queryset if is_in_use(img)]

    def delete_queryset(self, request, queryset):
        titles = self._in_use_titles(queryset)
        if titles:
            messages.error(
                request, "Nothing was deleted. Images in use: " + ", ".join(titles) + "."
            )
            return
        super().delete_queryset(request, queryset)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            description = actions["delete_selected"][2]

            def guarded_delete_selected(modeladmin, req, queryset):
                titles = modeladmin._in_use_titles(queryset)
                if titles:
                    modeladmin.message_user(
                        req,
                        "Nothing was deleted. Images in use: " + ", ".join(titles) + ".",
                        messages.ERROR,
                    )
                    return None
                return delete_selected(modeladmin, req, queryset)

            guarded_delete_selected.short_description = description
            actions["delete_selected"] = (guarded_delete_selected, "delete_selected", description)
        return actions


# Register the post_delete file cleanup (no apps.py change needed).
from pages import media_signals  # noqa: E402,F401
