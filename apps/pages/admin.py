import os
import subprocess
import tempfile
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from unfold.decorators import display
from core.admin import BaseModelAdmin
from pages.models import Page


@admin.register(Page)
class PageAdmin(BaseModelAdmin):
    list_display = ("slug", "language", "docx_status", "md_status", "updated_at")
    list_filter = ("language", "slug")
    search_fields = ("slug",)
    readonly_fields = ("converted_at", "updated_at", "convert_button")
    fieldsets = (
        (
            None,
            {
                "fields": ("slug", "language", "docx_file", "convert_button"),
            },
        ),
        (
            "Conversion info",
            {
                "fields": ("converted_at", "updated_at"),
            },
        ),
        (
            "Content (Markdown)",
            {
                "fields": ("content_md",),
                "description": "Edit Markdown directly, or upload a DOCX above and click Convert. "
                'Note: editing this field manually will clear the "Converted" status.',
            },
        ),
    )
    actions = ["convert_to_markdown"]

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if "content_md" in form.base_fields:
            form.base_fields["content_md"].widget.attrs.update(
                {
                    "rows": 30,
                    "style": "font-family: monospace; resize: vertical;",
                }
            )
        return form

    def save_model(self, request, obj, form, change):
        if "content_md" in form.changed_data:
            obj.converted_at = None
        super().save_model(request, obj, form, change)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:pk>/convert/",
                self.admin_site.admin_view(self._convert_view),
                name="pages-page-convert",
            ),
        ]
        return custom + urls

    def _convert_view(self, request, pk):
        obj = Page.objects.filter(pk=pk).first()
        if obj:
            self._run_conversion(request, obj)
        return HttpResponseRedirect(
            request.META.get("HTTP_REFERER", reverse("admin:pages_page_changelist"))
        )

    def _run_conversion(self, request, obj):
        if not obj.docx_file:
            self.message_user(request, f"{obj}: No DOCX file uploaded.", messages.WARNING)
            return
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            result = subprocess.run(
                [
                    "pandoc",
                    obj.docx_file.path,
                    "-f",
                    "docx",
                    "-t",
                    "markdown",
                    "--wrap=none",
                    "-o",
                    tmp_path,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                self.message_user(request, f"{obj}: pandoc error: {result.stderr}", messages.ERROR)
                return
            with open(tmp_path, "r", encoding="utf-8") as f:
                obj.content_md = f.read()
            obj.converted_at = timezone.now()
            obj.save()
            self.message_user(request, f"{obj}: Converted and saved.", messages.SUCCESS)
        except FileNotFoundError:
            self.message_user(
                request, f"{obj}: pandoc not installed. Rebuild the web container.", messages.ERROR
            )
        except subprocess.TimeoutExpired:
            self.message_user(request, f"{obj}: Conversion timed out.", messages.ERROR)
        except Exception as e:
            self.message_user(request, f"{obj}: Error — {e}", messages.ERROR)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def convert_button(self, obj):
        if not obj or not obj.pk:
            return mark_safe('<span style="color:#999">Save the page first.</span>')
        if not obj.docx_file:
            return mark_safe('<span style="color:#999">Upload a DOCX file first.</span>')
        url = reverse("admin:pages-page-convert", args=[obj.pk])
        return format_html(
            '<a href="{}" style="display:inline-block;background:#1565c0;color:#fff;padding:6px 16px;'
            'border-radius:4px;text-decoration:none;font-size:13px;font-weight:500">'
            "&#8635; Convert DOCX → Markdown</a>",
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
        if obj.content_md and not obj.converted_at:
            return mark_safe('<span style="color:#e65100">&#9998; Edited manually</span>')
        if obj.docx_file:
            url = reverse("admin:pages-page-convert", args=[obj.pk])
            return format_html(
                '<a href="{}" style="background:#1976d2;color:#fff;padding:2px 8px;border-radius:4px;text-decoration:none;font-size:12px">Convert</a>',
                url,
            )
        return mark_safe('<span style="color:#999">No content</span>')

    @admin.action(description="Convert uploaded DOCX to Markdown (bulk)")
    def convert_to_markdown(self, request, queryset):
        for obj in queryset:
            self._run_conversion(request, obj)
