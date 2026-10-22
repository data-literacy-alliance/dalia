"""Navigation data for the website: menu, footer columns and language switch.

``build_nav`` issues a single query; ancestors are taken from ``select_related`` so no further
queries are needed for the public paths.
"""

import unicodedata
from collections import defaultdict

from django.db.models import Q
from django.utils.encoding import iri_to_uri
from pages.models import Page

OTHER_LANGUAGE = {"en": "de", "de": "en"}
_ROMAN = (
    (1000, "M"),
    (900, "CM"),
    (500, "D"),
    (400, "CD"),
    (100, "C"),
    (90, "XC"),
    (50, "L"),
    (40, "XL"),
    (10, "X"),
    (9, "IX"),
    (5, "V"),
    (4, "IV"),
    (1, "I"),
)


def to_roman(number) -> str:
    """Roman numeral for 1..3999; anything else gives an empty string."""
    try:
        value = int(number)
    except (TypeError, ValueError):
        return ""
    if not 0 < value < 4000:
        return ""
    parts = []
    for size, symbol in _ROMAN:
        count, value = divmod(value, size)
        parts.append(symbol * count)
    return "".join(parts)


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def normalized_segments(page) -> list[str]:
    return [nfc(segment) for segment in page.public_segments()]


def ancestors_published(page) -> bool:
    node = page.parent
    while node is not None:
        if not node.is_published:
            return False
        node = node.parent
    return True


def menu_label(page) -> str:
    """Menu text: work fields get their roman numeral (``II: Communication``)."""
    if page.page_type == "work_field":
        numeral = to_roman(page.menu_order)
        if numeral:
            return f"{numeral}: {page.title}"
    return page.title


def _item(page) -> dict:
    return {
        "page": page,
        "title": page.nav_label,
        "url": page.nav_url,
        "children": [],
        "submenu_index": 0,
    }


def build_nav(lang: str) -> dict:
    """Return ``{"items", "work_fields", "legal_pages", "news_url", "newsletter_url"}`` for ``lang`` (one query).

    ``work_fields`` and ``legal_pages`` are ``Page`` objects; every page returned carries the extra
    attributes ``nav_label`` and ``nav_url`` (public path without the internal ``/site/`` prefix).
    """
    candidates = (
        Page.objects.website()
        .published()
        .filter(language=lang)
        .exclude(page_type="home")
        .filter(
            Q(show_in_menu=True)
            | Q(page_type__in=("work_field", "legal"))
            | Q(slug__in=("news", "newsletter"))
        )
        .select_related("parent__parent", "cover_image")
        .order_by("menu_order", "pk")
    )
    pages = [page for page in candidates if ancestors_published(page)]
    for page in pages:
        page.nav_label = menu_label(page)
        page.nav_url = iri_to_uri(page.get_public_path())

    menu_pages = [p for p in pages if p.show_in_menu]
    children = defaultdict(list)
    for page in menu_pages:
        if page.parent_id is not None:
            children[page.parent_id].append(page)

    items = []
    for page in menu_pages:
        if page.parent_id is not None:
            continue
        item = _item(page)
        item["children"] = [_item(child) for child in children.get(page.pk, [])]
        if item["children"]:
            item["submenu_index"] = sum(1 for i in items if i["children"]) + 1
        items.append(item)

    news = next((p for p in pages if p.slug == "news" and p.parent_id is None), None)
    newsletter = next((p for p in pages if p.slug == "newsletter" and p.parent_id is None), None)
    return {
        "items": items,
        "work_fields": [p for p in pages if p.page_type == "work_field"],
        "legal_pages": [p for p in pages if p.page_type == "legal"],
        "news_url": news.nav_url if news else "",
        "newsletter_url": newsletter.nav_url if newsletter else "",
    }


def alternate_language_path(page, lang: str) -> str:
    """Public path of ``page`` in the other language, else the other language home."""
    other = OTHER_LANGUAGE.get(lang, "en")
    fallback = f"/{other}"
    if page is None or page.page_type == "home":
        return fallback
    segments = normalized_segments(page)
    slugs = {segments[-1], unicodedata.normalize("NFD", segments[-1])}
    candidates = (
        Page.objects.website()
        .published()
        .filter(language=other, slug__in=slugs)
        .exclude(page_type="home")
        .select_related("parent__parent")
    )
    for candidate in candidates:
        if normalized_segments(candidate) == segments and ancestors_published(candidate):
            return iri_to_uri(candidate.get_public_path())
    return fallback
