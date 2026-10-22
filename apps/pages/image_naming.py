"""File naming for website media images."""

import os
import re
import unicodedata

from django.core.files.storage import FileSystemStorage
from django.utils import timezone
from django.utils.text import slugify

STEM_MAX_LEN = 100
_TRANSLITERATION = str.maketrans(
    {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss"}
)


def ascii_slug(text: str, max_len: int) -> str:
    """ASCII-only lowercase slug, trimmed to ``max_len`` at a dash when possible."""
    text = unicodedata.normalize("NFC", text or "").translate(_TRANSLITERATION)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"-{2,}", "-", slugify(text).lower()).strip("-")
    if len(slug) > max_len:
        cut = slug[:max_len]
        if slug[max_len] != "-" and "-" in cut:
            cut = cut.rsplit("-", 1)[0]
        slug = cut.strip("-")
    return slug or "image"


def _compute_stem(instance) -> str:
    override = getattr(instance, "_upload_stem", "")
    if override:
        return ascii_slug(override, STEM_MAX_LEN)
    title_slug = ascii_slug(instance.title, STEM_MAX_LEN)
    first_page = getattr(instance, "first_used_on", None)
    if first_page is None:
        return title_slug
    page_slug = ascii_slug(first_page.slug, STEM_MAX_LEN)
    return ascii_slug(f"{page_slug}-{title_slug}", STEM_MAX_LEN)


def media_image_upload_to(instance, filename: str) -> str:
    """``website/<year>/<stem>.<ext>`` with a deterministic, ASCII-only stem."""
    ext = os.path.splitext(filename)[1].lstrip(".").lower()
    year = timezone.localdate().year
    name = f"{_compute_stem(instance)}.{ext}" if ext else _compute_stem(instance)
    return f"website/{year}/{name}"


class NumberedSuffixStorage(FileSystemStorage):
    """On a name collision append ``-2``, ``-3``, ... before the extension."""

    def get_available_name(self, name, max_length=None):
        name = str(name).replace("\\", "/")
        root, ext = os.path.splitext(name)
        candidate = name
        counter = 1
        while self.exists(candidate) or (max_length and len(candidate) > max_length):
            counter += 1
            suffix = f"-{counter}"
            if max_length and len(root) + len(suffix) + len(ext) > max_length:
                root = root[: max_length - len(suffix) - len(ext)]
            candidate = f"{root}{suffix}{ext}"
        return candidate
