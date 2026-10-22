"""Website resolver: one view maps ``/site/<lang>/<slug path>`` to a published page and its template.

The view only answers requests that reached it through the internal ``/site/`` prefix on a website host.
Every redirect and link is built from ``Page.get_public_path()`` and never contains ``/site/``.
"""

import unicodedata

from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.db.models import F
from django.http import HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import render
from django.utils.cache import add_never_cache_headers
from django.utils.encoding import iri_to_uri
from pages.models import Page
from website.contact import handle_contact
from website.hosts import is_website_host
from website.navigation import (
    OTHER_LANGUAGE,
    alternate_language_path,
    ancestors_published,
    build_nav,
    nfc,
    normalized_segments,
)
from website.strings import get_strings

SITE_PREFIX = "/site/"
MAX_DEPTH = 3
MAX_SEGMENT_LENGTH = 200

PAGE_TEMPLATES = {
    "home": "website/pages/home.html",
    "work_field": "website/pages/work_field.html",
    "legal": "website/pages/legal.html",
    "event_list": "website/pages/event_list.html",
    "article_list": "website/pages/article_list.html",
    "article": "website/pages/article.html",
    "event": "website/pages/event.html",
}
FORM_TYPES = ("home", "work_field")
BLOCK_TYPES = ("home", "work_field", "event")
LIST_TYPES = ("event_list", "article_list")


def _is_site_request(request) -> bool:
    if not request.path_info.startswith(SITE_PREFIX):
        return False
    try:
        host = request.get_host()
    except DisallowedHost:
        return False
    return is_website_host(host)


def _search_portal_url() -> str:
    return settings.WEBSITE_SEARCH_PORTAL_URL.rstrip("/") + "/"


def _base_context(lang: str, page=None) -> dict:
    strings = get_strings(lang)
    return {
        "lang": lang,
        "S": strings,
        "page": page,
        "nav": build_nav(lang),
        "alt_lang_url": alternate_language_path(page, lang),
        "current_path": iri_to_uri(page.get_public_path()) if page is not None else f"/{lang}",
        "other_lang": OTHER_LANGUAGE[lang],
        "search_portal_url": _search_portal_url(),
        "MEDIA_URL": settings.MEDIA_URL,
        "page_title": strings["home_title"] if page is None else page.title,
    }


def not_found(request, lang: str):
    """Website-styled 404 (rendered by the view itself, not by the global handler)."""
    context = _base_context(lang)
    context["page_title"] = context["S"]["not_found_title"]
    return render(request, "website/404.html", context, status=404)


def _split_segments(path) -> list[str] | None:
    """NFC-normalised, non-empty path segments; ``None`` for impossible paths."""
    segments = [nfc(part) for part in (path or "").split("/") if part]
    if len(segments) > MAX_DEPTH:
        return None
    if any("\x00" in s or len(s) > MAX_SEGMENT_LENGTH for s in segments):
        return None
    return segments


def _published_website_pages():
    return Page.objects.website().published()


def _resolve(lang: str, segments: list[str]):
    """Published website page for ``lang`` + ``segments`` (whole ancestor chain published), or ``None``."""
    queryset = _published_website_pages().filter(language=lang)
    if not segments:
        return queryset.filter(page_type="home").select_related("cover_image", "category").first()
    slugs = {segments[-1], unicodedata.normalize("NFD", segments[-1])}
    candidates = (
        queryset.filter(slug__in=slugs)
        .exclude(page_type="home")
        .select_related("parent__parent", "cover_image", "category")
    )
    for candidate in candidates:
        if normalized_segments(candidate) == segments and ancestors_published(candidate):
            return candidate
    return None


def _grouped_blocks(page) -> dict:
    grouped: dict = {}
    for block in page.blocks.select_related("image"):
        grouped.setdefault(block.kind, []).append(block)
    return grouped


def _children(page) -> list:
    children = list(
        _published_website_pages()
        .filter(parent=page)
        .select_related("cover_image", "category")
        .order_by(F("date").desc(nulls_last=True), "menu_order", "pk")
    )
    for child in children:
        child.parent = page  # reuse the loaded ancestor chain for get_public_path()
    return children


def _folder_redirect(page):
    first = _published_website_pages().filter(parent=page).order_by("menu_order", "pk").first()
    if first is None:
        return None
    return HttpResponseRedirect(f"{page.get_public_path()}/{first.slug}")


def _contact_context(request, page, context):
    form, response, enabled = handle_contact(request, page)
    context.update(
        contact_form=form,
        contact_sent=request.GET.get("sent") == "1",
        contact_enabled=enabled,
        contact_form_id="contact-form"
        if page.page_type == "home"
        else f"contact-form-wf{page.menu_order}",
    )
    return response


def root_redirect(request):
    if not _is_site_request(request):
        return not_found(request, "en")
    return HttpResponseRedirect("/en")


def page_view(request, lang, path=None):
    if not _is_site_request(request):
        return not_found(request, lang)
    segments = _split_segments(path)
    page = _resolve(lang, segments) if segments is not None else None
    template = PAGE_TEMPLATES.get(page.page_type) if page is not None else None
    if page is not None and page.page_type == "folder":
        response = _folder_redirect(page)
        return response if response is not None else not_found(request, lang)
    if template is None:
        return not_found(request, lang)

    form_page = page.page_type in FORM_TYPES
    allowed = ["GET", "HEAD", "POST"] if form_page else ["GET", "HEAD"]
    if request.method not in allowed:
        return HttpResponseNotAllowed(allowed)

    context = _base_context(lang, page)
    context["canonical_url"] = settings.WEBSITE_PUBLIC_URL.rstrip("/") + iri_to_uri(
        page.get_public_path()
    )
    context["blocks"] = _grouped_blocks(page) if page.page_type in BLOCK_TYPES else {}
    context["children"] = _children(page) if page.page_type in LIST_TYPES else []
    if page.page_type == "home":
        context["page_title"] = context["S"]["home_title"]

    if form_page:
        redirect = _contact_context(request, page, context)
        response = redirect if redirect is not None else render(request, template, context)
        add_never_cache_headers(response)
        return response
    return render(request, template, context)
