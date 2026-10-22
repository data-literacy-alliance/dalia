import html
import re

from django import template
from django.conf import settings
from django.templatetags.static import static
from django.utils.encoding import iri_to_uri
from django.utils.html import format_html, strip_tags
from website.navigation import to_roman

register = template.Library()

_COLOR = re.compile(r"^(#[0-9A-Fa-f]{3,8}|[A-Za-z]{3,20})$")


@register.filter
def plain_text(value):
    """HTML to plain text (tags stripped, entities decoded); autoescape escapes it on output."""
    return html.unescape(strip_tags(str(value or "")))


@register.filter
def roman(value):
    """``2`` -> ``II`` (empty string outside 1..3999)."""
    return to_roman(value)


@register.filter
def public_url(value):
    """Absolute public URL of a website page (or of a path starting with ``/``)."""
    path = value if isinstance(value, str) else value.get_public_path()
    return settings.WEBSITE_PUBLIC_URL.rstrip("/") + iri_to_uri(path)


@register.filter
def alt(media_image, lang):
    """Alt text of a ``MediaImage`` in ``lang`` (empty for a missing image)."""
    return media_image.alt_for(lang) if media_image else ""


@register.filter
def catname(category, lang):
    """Label of an ``EventCategory`` in ``lang`` (empty for no category)."""
    return category.name_for(lang) if category else ""


def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@register.inclusion_tag("website/partials/icon_arrow.html")
def icon_arrow(width=17, height=15, rotate=0, fill="#000050"):
    return {
        "width": _int(width, 17),
        "height": _int(height, 15),
        "rotate": _int(rotate, 0),
        "fill": fill if _COLOR.match(str(fill)) else "#000050",
    }


# Work-field home card icons: file number == menu_order; (width, height) of the original inline SVG.
_WORK_FIELD_ICONS = {1: (33, 39), 2: (40, 40), 3: (41, 40), 4: (29, 40), 5: (36, 37)}


@register.simple_tag
def work_field_icon(work_field):
    """Static navy icon of a work field card (empty unless ``menu_order`` is 1-5)."""
    size = _WORK_FIELD_ICONS.get(work_field.menu_order)
    if size is None:
        return ""
    return format_html(
        '<img src="{}" alt="" class="icon-spacing" width="{}" height="{}">',
        static(f"website/images/icons/work-field-{work_field.menu_order}.svg"),
        size[0],
        size[1],
    )
