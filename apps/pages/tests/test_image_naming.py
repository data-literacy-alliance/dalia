from types import SimpleNamespace

import pytest
from pages.image_naming import NumberedSuffixStorage, ascii_slug, media_image_upload_to


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Größe & Maße", "groesse-masse"),
        ("Ärger Über Öl", "aerger-ueber-oel"),
        ("Straße", "strasse"),
        ("Café déjà", "cafe-deja"),
        ("😀😀", "image"),
        ("", "image"),
        ("a  --  b", "a-b"),
    ],
)
def test_ascii_slug(text, expected):
    assert ascii_slug(text, 100) == expected


def test_ascii_slug_trims_at_dash_boundary():
    assert ascii_slug("aaaa-bbbb-cccc", 11) == "aaaa-bbbb"


def test_ascii_slug_trims_hard_without_dash():
    assert ascii_slug("a" * 50, 10) == "a" * 10


def _instance(title, page_slug=None, stem=None):
    first = SimpleNamespace(slug=page_slug) if page_slug else None
    obj = SimpleNamespace(title=title, first_used_on=first)
    if stem:
        obj._upload_stem = stem
    return obj


def test_upload_to_uses_page_slug_and_title(settings):
    from django.utils import timezone

    year = timezone.localdate().year
    name = media_image_upload_to(_instance("Gruppenfoto Größe", "mein-event"), "X.JPG")
    assert name == f"website/{year}/mein-event-gruppenfoto-groesse.jpg"


def test_upload_to_without_page(settings):
    name = media_image_upload_to(_instance("Logo"), "x.png")
    assert name.endswith("/logo.png")


def test_upload_to_keeps_jpeg_extension():
    assert media_image_upload_to(_instance("t"), "x.JPEG").endswith("/t.jpeg")


def test_upload_to_long_stem_limited():
    name = media_image_upload_to(_instance("word " * 100, "p" * 150), "x.png")
    stem = name.rsplit("/", 1)[1].rsplit(".", 1)[0]
    assert len(stem) <= 100
    assert stem.isascii()


def test_upload_stem_hook_overrides():
    name = media_image_upload_to(_instance("ignored", "ignored", stem="Seite Ü image 1"), "x.png")
    assert name.endswith("/seite-ue-image-1.png")


def test_storage_numbered_suffix_on_collision(tmp_path):
    storage = NumberedSuffixStorage(location=str(tmp_path))
    names = []
    from django.core.files.base import ContentFile

    for _ in range(3):
        names.append(storage.save("website/2026/foo.png", ContentFile(b"x")))
    assert names == ["website/2026/foo.png", "website/2026/foo-2.png", "website/2026/foo-3.png"]


def test_storage_respects_max_length(tmp_path):
    storage = NumberedSuffixStorage(location=str(tmp_path))
    (tmp_path / "abcdefgh.png").write_bytes(b"x")
    result = storage.get_available_name("abcdefgh.png", max_length=12)
    assert len(result) <= 12 and result.endswith("-2.png")
