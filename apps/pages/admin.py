"""Admin for search-portal pages and website pages (two proxy admins, one shared base)."""

import os
import re
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path

from core.admin import BaseModelAdmin
from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.core.validators import FileExtensionValidator
from django.db import transaction
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST
from pages import rendering
from pages.models import (
    PLAIN_TEXT_BLOCK_KINDS,
    EventCategory,
    MediaImage,
    Page,
    PageBlock,
    SearchPage,
    WebsitePage,
)
from PIL import Image
from unfold.admin import StackedInline
from unfold.decorators import display

DOCX_TIMEOUT_SECONDS = 20
MAX_PANDOC_ERROR_CHARS = 300
MAX_SHOWN_WARNINGS = 10
SEARCH_DOCX_TARGET = "markdown"
# Mirrors the website reader so the writer never emits syntax the reader shows as text.
WEBSITE_DOCX_TARGET = rendering.MARKDOWN_READER
DOCX_MAIN_PART = "word/document.xml"
SEARCH_MEDIA_PARTS = ("pages", "media")
DIR_MODE = 0o755  # nginx (another user) must be able to read what is served from /media/
FILE_MODE = 0o644
_UNSAFE_NAME_CHARS = re.compile(r"[^A-Za-z0-9._-]")

BODY_FIELD_HELP = (
    "Markdown. Used by: home (intro text, optional), work field, legal, article and event "
    "pages (main text). Folder and list pages ignore it. Insert body images with the "
    "Markdown snippet from the image library (Image library > open an image > copy snippet)."
)
KIND_HELP = (
    "What each kind is for. hero: home, title + quote (plain text in body). mission, "
    "nfdi_intro, partners_intro: home, label + title + body. link_card: home, title + URL "
    "+ optional icon image. partner_logo / funder_logo: home, image + URL, label 'large' "
    "for a big logo. work_package: work field, label + title + body. section: event, label "
    "(may be blank) + body. agenda: event, label = time, title = text, body = sub-items "
    "one per line (plain text)."
)
AGENDA_BODY_HELP = "Markdown. For 'agenda' and 'hero' blocks the body is plain text (agenda: one sub-item per line)."


# -- validation helpers ------------------------------------------------------


def validate_docx_upload(uploaded) -> None:
    """Reject anything that is not a zip archive containing ``word/document.xml``."""
    FileExtensionValidator(["docx"])(uploaded)
    uploaded.seek(0)
    try:
        if not zipfile.is_zipfile(uploaded):
            raise ValidationError("The file is not a valid DOCX document.")
        uploaded.seek(0)
        with zipfile.ZipFile(uploaded) as archive:
            names = archive.namelist()
    except zipfile.BadZipFile as exc:
        raise ValidationError("The file is not a valid DOCX document.") from exc
    finally:
        uploaded.seek(0)
    if DOCX_MAIN_PART not in names:
        raise ValidationError("The file is not a valid DOCX document.")


def _render_error_text(exc) -> str:
    return f"Markdown could not be rendered: {str(exc)[:MAX_PANDOC_ERROR_CHARS]}"


# -- forms -------------------------------------------------------------------


class _PageFormBase(forms.ModelForm):
    site = None  # set by the concrete forms

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # A new proxy instance starts with the model default; model validation needs the real site.
        self.instance.site = self.site

    def clean_docx_file(self):
        uploaded = self.cleaned_data.get("docx_file")
        if isinstance(uploaded, UploadedFile):
            validate_docx_upload(uploaded)
        return uploaded

    def clean(self):
        cleaned = super().clean()
        self._check_slug_unique(cleaned)
        self._check_markdown(cleaned)
        return cleaned

    def _check_slug_unique(self, cleaned):
        slug, language = cleaned.get("slug"), cleaned.get("language")
        if not slug or not language:
            return
        clash = Page.objects.filter(site=self.site, slug=slug, language=language)
        if self.instance.pk:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            self.add_error("slug", "Slugs are unique per language across the whole site.")

    def _check_markdown(self, cleaned):
        """Search pages are stored as typed; only website pages are rendered."""


class SearchPageForm(_PageFormBase):
    site = Page.SITE_SEARCH

    class Meta:
        model = SearchPage
        fields = "__all__"  # noqa: DJ007 - the admin narrows fields from the fieldsets


class WebsitePageForm(_PageFormBase):
    site = Page.SITE_WEBSITE

    class Meta:
        model = WebsitePage
        fields = "__all__"  # noqa: DJ007 - the admin narrows fields from the fieldsets

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "category" in self.fields:
            self.fields["category"].queryset = EventCategory.objects.filter(
                Q(is_active=True) | Q(pk=self.instance.category_id)
            )

    def _check_markdown(self, cleaned):
        markdown = cleaned.get("content_md")
        if not markdown or "content_md" in self.errors:
            return
        try:
            rendering.render_markdown(markdown)
        except rendering.RenderError as exc:
            self.add_error("content_md", _render_error_text(exc))


class PageBlockInlineForm(forms.ModelForm):
    class Meta:
        model = PageBlock
        fields = "__all__"  # noqa: DJ007 - the admin narrows fields from the fieldsets

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "kind" in self.fields:
            self.fields["kind"].help_text = KIND_HELP
        if "body_md" in self.fields:
            self.fields["body_md"].help_text = AGENDA_BODY_HELP

    def clean(self):
        cleaned = super().clean()
        kind, markdown = cleaned.get("kind"), cleaned.get("body_md")
        if not markdown or not kind or kind in PLAIN_TEXT_BLOCK_KINDS:
            return cleaned
        if "body_md" in self.errors:
            return cleaned
        try:
            rendering.render_markdown(markdown)
        except rendering.RenderError as exc:
            self.add_error("body_md", _render_error_text(exc))
        return cleaned


class PageBlockInline(StackedInline):
    model = PageBlock
    form = PageBlockInlineForm
    extra = 0
    ordering = ("sort_order", "pk")
    autocomplete_fields = ("image",)
    fields = ("kind", "label", "title", "body_md", "image", "url", "sort_order")


# -- search-page media staging ---------------------------------------------------


class _StagedMediaDir:
    """New ``pages/media/<pk>/`` content built next to the live dir and swapped in on commit."""

    def __init__(self, final: Path, staging: Path):
        self.final = final
        self.staging = staging

    def commit(self) -> None:
        if not self.staging.exists():
            return
        has_files = any(self.staging.iterdir())
        backup = None
        if self.final.exists():
            backup = self.final.with_name(f".{self.final.name}-old-{uuid.uuid4().hex}")
            os.replace(self.final, backup)
        if has_files:
            try:
                os.replace(self.staging, self.final)
            except OSError:
                if backup is not None:
                    os.replace(backup, self.final)
                raise
        if backup is not None:
            shutil.rmtree(backup, ignore_errors=True)

    def discard(self) -> None:
        shutil.rmtree(self.staging, ignore_errors=True)


class _CreatedImageFiles:
    """Files of ``MediaImage`` rows made by one conversion; removed unless the save committed."""

    def __init__(self, names):
        self.names = list(names)
        self.committed = False

    def commit(self) -> None:
        self.committed = True

    def discard(self) -> None:
        if self.committed:
            return
        storage = MediaImage._meta.get_field("image").storage
        for name in self.names:
            try:
                storage.delete(name)
            except OSError:
                pass


def _unique_name(name: str, used: set[str]) -> str:
    safe = _UNSAFE_NAME_CHARS.sub("_", name)
    stem, ext = os.path.splitext(safe)
    candidate, counter = safe, 1
    while candidate in used:
        counter += 1
        candidate = f"{stem}-{counter}{ext}"
    used.add(candidate)
    return candidate


def _drop_leftover_refs(markdown: str, tmp: str) -> str:
    """Remove image references still pointing into the temp dir (e.g. via a skipped directory)."""
    pattern = re.compile(r"!\[[^\]]*\]\(\s*<?" + re.escape(tmp) + r"/[^)]*\)(?:\{[^}]*\})?")
    return pattern.sub("", markdown)


def _rel_name(file_path: Path) -> str:
    return "/".join(file_path.parts[-2:])


# -- admin base ------------------------------------------------------------------


class _PageAdminBase(BaseModelAdmin):
    docx_target = SEARCH_DOCX_TARGET
    readonly_fields = ("converted_at", "updated_at", "convert_button")
    actions = ["convert_to_markdown"]
    view_on_site = False
    site_notice = ""  # shown under the title so editors know which site the pages belong to

    def changelist_view(self, request, extra_context=None):
        extra_context = {"subtitle": self.site_notice, **(extra_context or {})}
        return super().changelist_view(request, extra_context)

    def add_view(self, request, form_url="", extra_context=None):
        extra_context = {"subtitle": self.site_notice, **(extra_context or {})}
        return super().add_view(request, form_url, extra_context)

    # -- form / save ---------------------------------------------------------

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if "content_md" in form.base_fields:
            form.base_fields["content_md"].widget.attrs.update(
                {"rows": 30, "style": "font-family: monospace; resize: vertical;"}
            )
        return form

    def save_model(self, request, obj, form, change):
        if "content_md" in form.changed_data:
            obj.converted_at = None
        super().save_model(request, obj, form, change)

    # -- convert view --------------------------------------------------------

    @property
    def convert_url_name(self) -> str:
        return f"pages-{self.model._meta.model_name}-convert"

    def _admin_url(self, name: str, *args) -> str:
        return reverse(f"{self.admin_site.name}:{name}", args=args)

    def get_urls(self):
        convert = path(
            "<int:pk>/convert/",
            self.admin_site.admin_view(require_POST(self._convert_view)),
            name=self.convert_url_name,
        )
        return [convert, *super().get_urls()]

    def _convert_view(self, request, pk):
        obj = self.get_queryset(request).filter(pk=pk).first()
        if obj is None:
            raise Http404
        if not self.has_change_permission(request, obj):
            raise PermissionDenied
        self._run_conversion(request, obj)
        change_name = f"pages_{self.model._meta.model_name}_change"
        return HttpResponseRedirect(self._admin_url(change_name, obj.pk))

    # -- conversion ----------------------------------------------------------

    def _run_conversion(self, request, obj):
        if not obj.docx_file:
            self.message_user(request, f"{obj}: No DOCX file uploaded.", messages.WARNING)
            return
        tmp = tempfile.mkdtemp(prefix="docx-")  # outside MEDIA_ROOT
        try:
            warnings = self._convert(request, obj, tmp)
        except rendering.RenderError as exc:
            self.message_user(
                request,
                format_html("{}: pandoc error: {}", obj, str(exc)[:MAX_PANDOC_ERROR_CHARS]),
                messages.ERROR,
            )
            return
        except OSError:
            self.message_user(request, f"{obj}: The DOCX file could not be read.", messages.ERROR)
            return
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.message_user(request, f"{obj}: Converted and saved.", messages.SUCCESS)
        self._show_warnings(request, warnings)

    def _convert(self, request, obj, tmp) -> list[str]:
        from pages import docx_media  # lazy: keeps admin import light

        markdown = rendering.run_pandoc(
            [
                obj.docx_file.path,
                "-f",
                "docx",
                "-t",
                self.docx_target,
                "--wrap=none",
                "--sandbox",
                f"--extract-media={tmp}",
            ],
            timeout=DOCX_TIMEOUT_SECONDS,
        )
        accepted, skipped = docx_media.collect_extracted_images(tmp)
        staged = None
        with transaction.atomic():
            try:
                markdown, store_warnings, staged = self._store_images(
                    obj, accepted, markdown, request.user
                )
                markdown = docx_media.strip_image_refs(markdown, skipped)
                obj.content_md = _drop_leftover_refs(markdown, str(tmp))
                obj.converted_at = timezone.now()
                obj.save()
                if staged is not None:
                    staged.commit()
            finally:
                if staged is not None:
                    staged.discard()
        return [*skipped, *store_warnings]

    def _store_images(self, obj, accepted, markdown, user):
        """Return ``(markdown, warnings, staged_or_None)``; implemented per site."""
        raise NotImplementedError

    def _show_warnings(self, request, warnings):
        for warning in warnings[:MAX_SHOWN_WARNINGS]:
            self.message_user(request, format_html("{}", warning), messages.WARNING)
        extra = len(warnings) - MAX_SHOWN_WARNINGS
        if extra > 0:
            self.message_user(request, f"... and {extra} more warnings.", messages.WARNING)

    @admin.action(description="Convert uploaded DOCX to Markdown (bulk)", permissions=["change"])
    def convert_to_markdown(self, request, queryset):
        for obj in queryset:
            if self.has_change_permission(request, obj):
                self._run_conversion(request, obj)

    # -- readonly widgets ----------------------------------------------------

    def convert_button(self, obj):
        if not obj or not obj.pk:
            return mark_safe('<span style="color:#999">Save the page first.</span>')
        if not obj.docx_file:
            return mark_safe('<span style="color:#999">Upload a DOCX file and save first.</span>')
        url = self._admin_url(self.convert_url_name, obj.pk)
        return format_html(
            '<button type="submit" formaction="{}" formmethod="post" formnovalidate '
            'style="background:#1565c0;color:#fff;padding:6px 16px;border-radius:4px;'
            'border:0;cursor:pointer;font-size:13px;font-weight:500">'
            "&#8635; Convert DOCX → Markdown</button> "
            '<span style="color:#999">Converts the saved file; unsaved edits are not submitted.</span>',
            url,
        )

    convert_button.short_description = "Convert"

    @display(description="DOCX")
    def docx_status(self, obj):
        if obj.docx_file:
            return mark_safe('<span style="color:#2e7d32">&#10003; Uploaded</span>')
        return mark_safe('<span style="color:#999">—</span>')

    @display(description="MD Status")
    def md_status(self, obj):
        if obj.content_md and obj.converted_at:
            return mark_safe('<span style="color:#2e7d32">&#10003; Converted</span>')
        if obj.content_md:
            return mark_safe('<span style="color:#e65100">&#9998; Edited manually</span>')
        if obj.docx_file:
            return mark_safe('<span style="color:#1976d2">DOCX uploaded, not converted</span>')
        return mark_safe('<span style="color:#999">No content</span>')


@admin.register(SearchPage)
class SearchPageAdmin(_PageAdminBase):
    form = SearchPageForm
    site_notice = "These pages are shown in the search portal (search.dalia.education)."
    docx_target = SEARCH_DOCX_TARGET
    list_display = ("slug", "language", "docx_status", "md_status", "updated_at")
    list_filter = ("language", "slug")
    search_fields = ("slug",)
    fieldsets = (
        (None, {"fields": ("slug", "language", "docx_file", "convert_button")}),
        ("Conversion info", {"fields": ("converted_at", "updated_at")}),
        (
            "Content (Markdown)",
            {
                "fields": ("content_md",),
                "description": "Edit Markdown directly, or upload a DOCX above and click Convert. "
                'Note: editing this field manually will clear the "Converted" status.',
            },
        ),
    )

    def _store_images(self, obj, accepted, markdown, user):
        """Re-encode accepted images into a staged ``pages/media/<pk>/`` and rewrite the paths."""
        from pages import docx_media  # lazy
        from pages.image_processing import reencode_image
        from pages.validators import validate_image_upload

        parent = Path(settings.MEDIA_ROOT).joinpath(*SEARCH_MEDIA_PARTS)
        parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{obj.pk}-new-", dir=parent))
        staged = _StagedMediaDir(parent / str(obj.pk), staging)
        warnings: list[str] = []
        used: set[str] = set()
        try:
            os.chmod(staging, DIR_MODE)
            for file_path in accepted:
                try:
                    with open(file_path, "rb") as fh:
                        data = reencode_image(fh, validate_image_upload(fh, file_path.name))
                except (ValidationError, OSError, ValueError, Image.DecompressionBombError) as exc:
                    reason = (
                        "; ".join(exc.messages) if isinstance(exc, ValidationError) else str(exc)
                    )
                    warnings.append(f"{_rel_name(file_path)}: skipped ({reason})")
                    markdown = docx_media.strip_image_refs(markdown, [_rel_name(file_path)])
                    continue
                name = _unique_name(file_path.name, used)
                target = staging / name
                target.write_bytes(data)
                os.chmod(target, FILE_MODE)
                url = f"{settings.MEDIA_URL}pages/media/{obj.pk}/{name}"
                markdown = docx_media._rewrite_refs(markdown, file_path, url)
        except BaseException:
            staged.discard()
            raise
        return markdown, warnings, staged


@admin.register(WebsitePage)
class WebsitePageAdmin(_PageAdminBase):
    form = WebsitePageForm
    site_notice = "These pages are shown on dalia.education."
    docx_target = WEBSITE_DOCX_TARGET
    inlines = [PageBlockInline]
    list_display = (
        "title",
        "language",
        "page_type",
        "parent",
        "is_published",
        "show_in_menu",
        "menu_order",
        "date",
        "updated_at",
    )
    list_select_related = ("parent",)
    list_filter = ("page_type", "language", "is_published", "category")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("cover_image",)
    fieldsets = (
        (
            "Basics",
            {
                "fields": (
                    "page_type",
                    "language",
                    "title",
                    "slug",
                    "parent",
                    "is_published",
                    "show_in_menu",
                    "menu_order",
                ),
                "description": "Slugs are unique per language across the whole website.",
            },
        ),
        (
            "Listing",
            {
                "fields": ("summary", "cover_image", "date", "date_end"),
                "description": "Used on list pages (articles, events) and cards. "
                "Date is required for events.",
            },
        ),
        (
            "Event",
            {
                "fields": ("category", "date_text", "time_text", "location", "address"),
                "description": "Event pages only. Date text overrides the formatted date.",
            },
        ),
        ("Article", {"fields": ("authors",), "description": "Article pages only."}),
        (
            "Body",
            {
                "fields": ("docx_file", "convert_button", "content_md"),
                "description": BODY_FIELD_HELP,
            },
        ),
        ("Conversion info", {"fields": ("converted_at", "updated_at"), "classes": ["collapse"]}),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent":
            kwargs["queryset"] = Page.objects.filter(site=Page.SITE_WEBSITE)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def view_on_site(self, obj):
        return obj.get_absolute_url() if obj.is_published else None

    def _store_images(self, obj, accepted, markdown, user):
        from pages import docx_media  # lazy

        before = set(MediaImage.objects.values_list("pk", flat=True))
        try:
            markdown, warnings = docx_media.register_extracted_media(obj, accepted, markdown, user)
        finally:
            created = list(
                MediaImage.objects.exclude(pk__in=before).values_list("image", flat=True)
            )
        return markdown, warnings, _CreatedImageFiles(created)


from pages import admin_event_category, admin_media  # noqa: E402,F401
