import hashlib
import os
import re

from curation.models.base import Activatable, TimeStampedModel, UUIDMixin
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import MaxLengthValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from pages.image_naming import NumberedSuffixStorage, media_image_upload_to
from pages.validators import MAX_MARKDOWN_CHARS, validate_image_field, validate_image_upload

MAX_PAGE_DEPTH = 3
# Block kinds whose body_md is plain text and therefore not rendered to HTML.
PLAIN_TEXT_BLOCK_KINDS = ("agenda", "hero")


class EventCategory(UUIDMixin, Activatable, TimeStampedModel):
    name_en = models.CharField(max_length=100, unique=True)
    name_de = models.CharField(max_length=100)
    description = models.TextField(blank=True, help_text="Shown in the admin only.")
    color = models.CharField(
        max_length=7,
        validators=[RegexValidator(r"^#[0-9A-Fa-f]{6}$", "Enter a hex color such as #FF7B42.")],
        help_text="Hex color code, e.g. #FF7B42",
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("order", "name_en")
        verbose_name_plural = "Event categories"

    def __str__(self):
        return self.name_en

    def name_for(self, lang: str) -> str:
        return self.name_de if lang == "de" else self.name_en


class MediaImage(models.Model):
    image = models.ImageField(
        upload_to=media_image_upload_to,
        storage=NumberedSuffixStorage(),
        max_length=255,
        validators=[validate_image_field],
        help_text=(
            "File names are deterministic: an image uploaded for an unpublished page is "
            "reachable at a guessable /media/ URL before the page is published. Do not "
            "upload confidential images before publication."
        ),
    )
    title = models.CharField(max_length=200)
    alt_en = models.CharField(max_length=300)
    alt_de = models.CharField(max_length=300)
    first_used_on = models.ForeignKey(
        "Page",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="first_images",
        limit_choices_to={"site": "website"},
        help_text="Only used to build the file name at upload time.",
    )
    sha256 = models.CharField(max_length=64, db_index=True, editable=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ("-uploaded_at",)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self._state.adding and not self.pk:
            self._prepare_new_image()
        super().save(*args, **kwargs)

    def _prepare_new_image(self):
        """Validate, strip metadata by re-encoding and hash the stored bytes."""
        from pages.image_processing import reencode_image  # lazy: owned by another module

        original_name = os.path.basename(self.image.name)
        self.image.open("rb")
        try:
            fmt = validate_image_upload(self.image.file, original_name)
            data = reencode_image(self.image.file, fmt)
        finally:
            self.image.close()
        self.sha256 = hashlib.sha256(data).hexdigest()
        self.image = ContentFile(data, name=original_name)

    def alt_for(self, lang: str) -> str:
        return self.alt_de if lang == "de" else self.alt_en

    def markdown_snippet(self, lang: str) -> str:
        alt = re.sub(r"\s*[\r\n]+\s*", " ", self.alt_for(lang))
        alt = re.sub(r"([\\\[\]])", r"\\\1", alt)
        return f"![{alt}]({self.image.url})"


class PageQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)

    def website(self):
        return self.filter(site=Page.SITE_WEBSITE)

    def search(self):
        return self.filter(site=Page.SITE_SEARCH)


class Page(models.Model):
    SITE_SEARCH = "search"
    SITE_WEBSITE = "website"
    SITE_CHOICES = [(SITE_SEARCH, "Search portal"), (SITE_WEBSITE, "Website (dalia.education)")]

    LANGUAGE_CHOICES = [
        ("de", "German"),
        ("en", "English"),
    ]

    PAGE_TYPE_CHOICES = [
        ("home", "Home"),
        ("folder", "Folder"),
        ("work_field", "Work field"),
        ("legal", "Legal"),
        ("event_list", "Event list"),
        ("article_list", "Article list"),
        ("article", "Article"),
        ("event", "Event"),
    ]

    site = models.CharField(max_length=10, choices=SITE_CHOICES, default=SITE_SEARCH, db_index=True)
    slug = models.SlugField(max_length=200, allow_unicode=True)
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES)
    page_type = models.CharField(max_length=20, choices=PAGE_TYPE_CHOICES, blank=True)
    title = models.CharField(max_length=300, blank=True)
    summary = models.TextField(blank=True)
    content_md = models.TextField(blank=True, validators=[MaxLengthValidator(MAX_MARKDOWN_CHARS)])
    docx_file = models.FileField(upload_to="pages/docx/", blank=True, null=True)
    converted_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    cover_image = models.ForeignKey(
        MediaImage,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="cover_for_pages",
    )
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    date = models.DateField(null=True, blank=True)
    date_end = models.DateField(null=True, blank=True)
    date_text = models.CharField(max_length=100, blank=True)
    time_text = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=300, blank=True)
    address = models.TextField(blank=True)
    authors = models.CharField(max_length=500, blank=True)
    category = models.ForeignKey(
        EventCategory, null=True, blank=True, on_delete=models.PROTECT, related_name="events"
    )
    menu_order = models.PositiveIntegerField(default=0)
    show_in_menu = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    content_html = models.TextField(blank=True, editable=False)

    objects = PageQuerySet.as_manager()

    class Meta:
        verbose_name = "Page"
        verbose_name_plural = "Pages"
        ordering = ["slug", "language"]
        constraints = [
            models.UniqueConstraint(
                fields=["site", "slug", "language"], name="pages_page_site_slug_lang_uniq"
            ),
            models.UniqueConstraint(
                fields=["site", "language"],
                condition=Q(page_type="home"),
                name="pages_page_one_home_per_lang",
            ),
        ]
        indexes = [
            models.Index(
                fields=["site", "language", "is_published"], name="pages_page_site_lang_pub"
            ),
            models.Index(fields=["parent", "is_published"], name="pages_page_parent_pub"),
        ]

    def __str__(self):
        return f"{self.slug} ({self.get_language_display()})"

    def save(self, *args, **kwargs):
        if self.is_website:
            from pages.rendering import render_markdown  # lazy: owned by another module

            self.content_html = render_markdown(self.content_md) if self.content_md else ""
            update_fields = kwargs.get("update_fields")
            if update_fields is not None and "content_md" in update_fields:
                kwargs["update_fields"] = {*update_fields, "content_html"}
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        if not self.is_website:
            return None
        return settings.WEBSITE_PUBLIC_URL.rstrip("/") + self.get_public_path()

    # -- website helpers -------------------------------------------------

    @property
    def is_website(self) -> bool:
        return self.site == self.SITE_WEBSITE

    def _parent_chain(self):
        """Ancestors from the direct parent upwards; cycle-safe (may reach ``self``)."""
        seen = set()
        node = self.parent
        while node is not None and node.pk not in seen:
            seen.add(node.pk)
            yield node
            node = node.parent

    def public_segments(self) -> list[str]:
        if self.page_type == "home":
            return []
        return [a.slug for a in reversed(list(self._parent_chain()))] + [self.slug]

    def get_public_path(self) -> str:
        segments = self.public_segments()
        return "/".join(["", self.language, *segments]) if segments else f"/{self.language}"

    @property
    def is_past(self) -> bool:
        if self.page_type != "event" or not self.date:
            return False
        return (self.date_end or self.date) < timezone.localdate()

    @property
    def display_date(self) -> str:
        if self.date_text:
            return self.date_text
        if not self.date:
            return ""
        start, end = self.date, self.date_end
        if not end or end == start:
            return start.strftime("%d.%m.%Y")
        if (start.year, start.month) == (end.year, end.month):
            return f"{start:%d}. - {end:%d.%m.%Y}"
        if start.year == end.year:
            return f"{start:%d.%m.} - {end:%d.%m.%Y}"
        return f"{start:%d.%m.%Y} - {end:%d.%m.%Y}"

    def blocks_by_kind(self) -> dict[str, list["PageBlock"]]:
        grouped: dict[str, list[PageBlock]] = {}
        for block in self.blocks.all():
            grouped.setdefault(block.kind, []).append(block)
        return grouped

    # -- validation / persistence ---------------------------------------

    def clean(self):
        super().clean()
        if not self.is_website:
            return
        errors: dict[str, str] = {}
        self._clean_parent(errors)
        self._clean_type_rules(errors)
        if errors:
            raise ValidationError(errors)

    def _clean_parent(self, errors):
        parent = self.parent
        if self.page_type == "home":
            if parent is not None:
                errors["parent"] = "The home page cannot have a parent."
            if self._other_home_exists():
                errors["page_type"] = "A home page already exists for this language."
            return
        if parent is None:
            return
        if parent.site != self.SITE_WEBSITE:
            errors["parent"] = "The parent must be a website page."
        elif parent.language != self.language:
            errors["parent"] = "The parent must have the same language."
        elif parent.page_type == "home":
            errors["parent"] = "The home page cannot be a parent."
        elif self.pk and any(a.pk == self.pk for a in self._parent_chain()):
            errors["parent"] = "A page cannot be its own ancestor."
        elif len(list(self._parent_chain())) + 1 > MAX_PAGE_DEPTH:
            errors["parent"] = f"Pages can be nested at most {MAX_PAGE_DEPTH} levels deep."

    def _other_home_exists(self) -> bool:
        qs = Page.objects.filter(site=self.SITE_WEBSITE, language=self.language, page_type="home")
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        return qs.exists()

    def _clean_type_rules(self, errors):
        if self.page_type and self.page_type != "home" and not self.title:
            errors["title"] = "A title is required for this page type."
        if self.page_type == "event" and not self.date:
            errors["date"] = "Events require a date."
        if self.date and self.date_end and self.date_end < self.date:
            errors["date_end"] = "The end date cannot be before the start date."
        if self.category_id and self.page_type != "event":
            errors["category"] = "A category is only allowed on event pages."


class _SiteManager(models.Manager.from_queryset(PageQuerySet)):
    def __init__(self, site):
        super().__init__()
        self._site = site

    def get_queryset(self):
        return super().get_queryset().filter(site=self._site)


class SearchPage(Page):
    objects = _SiteManager(Page.SITE_SEARCH)

    class Meta:
        proxy = True
        verbose_name = "Search portal page"
        verbose_name_plural = "Search portal pages"

    def save(self, *args, **kwargs):
        self.site = self.SITE_SEARCH
        super().save(*args, **kwargs)


class WebsitePage(Page):
    objects = _SiteManager(Page.SITE_WEBSITE)

    class Meta:
        proxy = True
        verbose_name = "Website page"
        verbose_name_plural = "Website pages (dalia.education)"

    def save(self, *args, **kwargs):
        self.site = self.SITE_WEBSITE
        super().save(*args, **kwargs)


class PageBlock(models.Model):
    KIND_CHOICES = [
        ("hero", "Hero"),
        ("mission", "Mission"),
        ("nfdi_intro", "NFDI intro"),
        ("link_card", "Link card"),
        ("partners_intro", "Partners intro"),
        ("partner_logo", "Partner logo"),
        ("funder_logo", "Funder logo"),
        ("work_package", "Work package"),
        ("section", "Section"),
        ("agenda", "Agenda item"),
    ]

    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="blocks")
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    label = models.CharField(max_length=200, blank=True)
    title = models.CharField(max_length=300, blank=True)
    body_md = models.TextField(blank=True, validators=[MaxLengthValidator(MAX_MARKDOWN_CHARS)])
    body_html = models.TextField(blank=True, editable=False)
    image = models.ForeignKey(
        MediaImage, null=True, blank=True, on_delete=models.PROTECT, related_name="blocks"
    )
    url = models.URLField(max_length=500, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pk"]

    def __str__(self):
        return f"{self.get_kind_display()}: {self.title or self.label}".strip()

    def save(self, *args, **kwargs):
        if self.kind in PLAIN_TEXT_BLOCK_KINDS or not self.body_md:
            self.body_html = ""
        else:
            from pages.rendering import render_markdown  # lazy: owned by another module

            self.body_html = render_markdown(self.body_md)
        super().save(*args, **kwargs)
