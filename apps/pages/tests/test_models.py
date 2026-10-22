import datetime
import hashlib
import io
import sys
import types

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.utils import timezone
from pages.models import (
    EventCategory,
    MediaImage,
    Page,
    PageBlock,
    SearchPage,
    WebsitePage,
)
from pages.validators import MAX_MARKDOWN_CHARS
from PIL import Image

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def fake_pipeline(monkeypatch):
    """Stand-ins for the rendering and image modules owned by another slice."""
    render = types.ModuleType("pages.rendering")
    render.render_markdown = lambda md: f"<p>{md}</p>"
    monkeypatch.setitem(sys.modules, "pages.rendering", render)
    proc = types.ModuleType("pages.image_processing")
    proc.calls = []

    def reencode_image(file, fmt):
        proc.calls.append(fmt)
        return b"REENCODED-" + fmt.encode()

    proc.reencode_image = reencode_image
    monkeypatch.setitem(sys.modules, "pages.image_processing", proc)
    return proc


def make_page(slug="p", lang="en", **kw):
    kw.setdefault("site", "website")
    kw.setdefault("page_type", "legal")
    kw.setdefault("title", slug)
    return Page.objects.create(slug=slug, language=lang, **kw)


# --- EventCategory -------------------------------------------------------


def test_category_color_validator_rejects_css_injection():
    cat = EventCategory(name_en="X", name_de="X", color="red; background:url(x)")
    with pytest.raises(ValidationError) as exc:
        cat.full_clean()
    assert "color" in exc.value.message_dict


def test_category_valid_and_name_for():
    cat = EventCategory(name_en="Workshop", name_de="Werkstatt", color="#FF7B42")
    cat.full_clean()
    assert cat.name_for("de") == "Werkstatt"
    assert cat.name_for("en") == "Workshop"
    assert str(cat) == "Workshop"


def test_category_duplicate_name_en_rejected():
    EventCategory.objects.create(name_en="A", name_de="A", color="#000000")
    dup = EventCategory(name_en="A", name_de="B", color="#000000")
    with pytest.raises(ValidationError):
        dup.full_clean()


def test_no_categories_seeded():
    assert EventCategory.objects.count() == 0


# --- Page constraints and validation -------------------------------------


def test_long_unicode_slug_saves():
    slug = "20241010_wo-stehen-die-datenkompetenz-qualitätssicherung-" + "x" * 80
    assert len(slug) > 130
    page = make_page(slug)
    assert Page.objects.get(pk=page.pk).slug == slug


def test_duplicate_site_slug_language_rejected():
    make_page("dup")
    with pytest.raises(IntegrityError), transaction.atomic():
        make_page("dup")


def test_same_slug_allowed_across_sites():
    make_page("privacy-policy")
    Page.objects.create(slug="privacy-policy", language="en")  # search site


def test_second_home_per_language_rejected_by_db():
    make_page("home", page_type="home", title="")
    with pytest.raises(IntegrityError), transaction.atomic():
        make_page("home2", page_type="home", title="")
    make_page("home-de", lang="de", page_type="home", title="")


def test_second_home_friendly_clean_error():
    make_page("home", page_type="home", title="")
    other = Page(site="website", slug="h2", language="en", page_type="home")
    with pytest.raises(ValidationError) as exc:
        other.clean()
    assert "page_type" in exc.value.message_dict


def test_home_with_parent_rejected():
    folder = make_page("f", page_type="folder")
    home = Page(site="website", slug="h", language="en", page_type="home", parent=folder)
    with pytest.raises(ValidationError) as exc:
        home.clean()
    assert "parent" in exc.value.message_dict


def test_parent_wrong_language_rejected():
    folder = make_page("f", lang="de", page_type="folder")
    child = Page(
        site="website", slug="c", language="en", page_type="legal", title="c", parent=folder
    )
    with pytest.raises(ValidationError) as exc:
        child.clean()
    assert "same language" in exc.value.message_dict["parent"][0]


def test_parent_search_site_rejected():
    parent = Page.objects.create(slug="s", language="en")
    child = Page(
        site="website", slug="c", language="en", page_type="legal", title="c", parent=parent
    )
    with pytest.raises(ValidationError) as exc:
        child.clean()
    assert "website page" in exc.value.message_dict["parent"][0]


def test_cycle_rejected():
    a = make_page("a", page_type="folder")
    b = make_page("b", page_type="folder", parent=a)
    a.parent = b
    with pytest.raises(ValidationError) as exc:
        a.clean()
    assert "ancestor" in exc.value.message_dict["parent"][0]


def test_self_parent_rejected():
    a = make_page("a", page_type="folder")
    a.parent = a
    with pytest.raises(ValidationError):
        a.clean()


def test_depth_limit():
    l1 = make_page("l1", page_type="folder")
    l2 = make_page("l2", page_type="folder", parent=l1)
    l3 = make_page("l3", page_type="folder", parent=l2)
    l4 = Page(site="website", slug="l4", language="en", page_type="legal", title="l4", parent=l3)
    with pytest.raises(ValidationError) as exc:
        l4.clean()
    assert "deep" in exc.value.message_dict["parent"][0]
    ok = Page(site="website", slug="ok", language="en", page_type="legal", title="ok", parent=l2)
    ok.clean()


def test_non_home_requires_title():
    with pytest.raises(ValidationError) as exc:
        Page(site="website", slug="x", language="en", page_type="legal").clean()
    assert "title" in exc.value.message_dict


def test_event_requires_date_and_end_not_before_start():
    with pytest.raises(ValidationError) as exc:
        Page(site="website", slug="e", language="en", page_type="event", title="e").clean()
    assert "date" in exc.value.message_dict
    d = datetime.date(2026, 5, 2)
    with pytest.raises(ValidationError) as exc:
        Page(
            site="website",
            slug="e",
            language="en",
            page_type="event",
            title="e",
            date=d,
            date_end=datetime.date(2026, 5, 1),
        ).clean()
    assert "date_end" in exc.value.message_dict


def test_category_only_on_event_pages():
    cat = EventCategory.objects.create(name_en="A", name_de="A", color="#000000")
    page = Page(
        site="website", slug="a", language="en", page_type="article", title="a", category=cat
    )
    with pytest.raises(ValidationError) as exc:
        page.clean()
    assert "category" in exc.value.message_dict
    Page(
        site="website",
        slug="ev",
        language="en",
        page_type="event",
        title="e",
        date=datetime.date(2026, 1, 1),
        category=cat,
    ).clean()


def test_search_page_clean_has_no_website_rules():
    Page(slug="s", language="en").clean()


def test_markdown_over_limit_rejected():
    page = Page(slug="big", language="en", content_md="x" * (MAX_MARKDOWN_CHARS + 1))
    with pytest.raises(ValidationError) as exc:
        page.full_clean()
    assert "content_md" in exc.value.message_dict
    Page(slug="big", language="en", content_md="x" * MAX_MARKDOWN_CHARS).full_clean()


def test_block_markdown_over_limit_rejected():
    page = make_page("bp")
    block = PageBlock(page=page, kind="section", body_md="x" * (MAX_MARKDOWN_CHARS + 1))
    with pytest.raises(ValidationError) as exc:
        block.full_clean()
    assert "body_md" in exc.value.message_dict


# --- Paths, dates, queryset, proxies --------------------------------------


def test_public_paths():
    home = make_page("home", page_type="home", title="")
    folder = make_page("work", page_type="folder")
    child = make_page("qualitätssicherung", page_type="work_field", parent=folder)
    assert home.public_segments() == []
    assert home.get_public_path() == "/en"
    assert child.public_segments() == ["work", "qualitätssicherung"]
    assert child.get_public_path() == "/en/work/qualitätssicherung"


def test_get_absolute_url(settings):
    settings.WEBSITE_PUBLIC_URL = "https://example.test/"
    page = make_page("foo")
    assert page.get_absolute_url() == "https://example.test/en/foo"
    assert Page.objects.create(slug="s", language="en").get_absolute_url() is None


@pytest.mark.parametrize(
    "start,end,expected",
    [
        ((2025, 8, 25), None, "25.08.2025"),
        ((2025, 8, 25), (2025, 8, 25), "25.08.2025"),
        ((2025, 9, 4), (2025, 9, 5), "04. - 05.09.2025"),
        ((2024, 1, 31), (2024, 2, 1), "31.01. - 01.02.2024"),
        ((2024, 12, 31), (2025, 1, 2), "31.12.2024 - 02.01.2025"),
    ],
)
def test_display_date(start, end, expected):
    page = Page(date=datetime.date(*start), date_end=datetime.date(*end) if end else None)
    assert page.display_date == expected


def test_display_date_text_overrides_and_empty():
    assert (
        Page(date=datetime.date(2025, 1, 1), date_text="Spring 2025").display_date == "Spring 2025"
    )
    assert Page().display_date == ""


def test_is_past_boundary():
    today = timezone.localdate()
    ev = Page(page_type="event", date=today)
    assert ev.is_past is False
    assert Page(page_type="event", date=today - datetime.timedelta(days=1)).is_past is True
    assert (
        Page(page_type="event", date=today - datetime.timedelta(days=3), date_end=today).is_past
        is False
    )
    assert Page(page_type="article", date=today - datetime.timedelta(days=9)).is_past is False


def test_queryset_helpers_and_proxies():
    w = make_page("w", is_published=True)
    make_page("w2")
    s = Page.objects.create(slug="s", language="en", is_published=True)
    assert set(Page.objects.website().published()) == {w}
    assert list(Page.objects.search()) == [s]
    assert WebsitePage.objects.count() == 2
    assert SearchPage.objects.count() == 1
    forced = SearchPage(slug="forced", language="en", site="website")
    forced.save()
    assert Page.objects.get(slug="forced").site == "search"
    forced_w = WebsitePage(slug="fw", language="en", page_type="legal", title="t")
    forced_w.save()
    assert Page.objects.get(slug="fw").site == "website"
    assert WebsitePage._meta.verbose_name_plural == "Website pages (dalia.education)"
    assert SearchPage._meta.verbose_name_plural == "Search portal pages"


def test_save_renders_html_for_website_only():
    w = make_page("w", content_md="hello")
    assert w.content_html == "<p>hello</p>"
    s = Page.objects.create(slug="s", language="en", content_md="hello")
    assert s.content_html == ""
    assert make_page("empty", content_md="").content_html == ""


def test_save_does_not_import_renderer_for_search_pages(monkeypatch):
    monkeypatch.delitem(sys.modules, "pages.rendering")
    monkeypatch.setitem(sys.modules, "pages.rendering", None)  # import would raise
    Page.objects.create(slug="s", language="en", content_md="x")


def test_blocks_by_kind_and_html():
    page = make_page("home", page_type="home", title="")
    PageBlock.objects.create(page=page, kind="partner_logo", sort_order=2)
    PageBlock.objects.create(page=page, kind="partner_logo", sort_order=1, label="large")
    b = PageBlock.objects.create(page=page, kind="mission", body_md="m")
    agenda = PageBlock.objects.create(page=page, kind="agenda", body_md="a\nb")
    grouped = page.blocks_by_kind()
    assert [x.label for x in grouped["partner_logo"]] == ["large", ""]
    assert b.body_html == "<p>m</p>"
    assert agenda.body_html == ""


# --- MediaImage -----------------------------------------------------------


def _png(size=(8, 8)):
    buf = io.BytesIO()
    Image.new("RGB", size, "blue").save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def media_root(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    return tmp_path


def _make_image(title="Gruppenfoto", name="orig.png", data=None, **kw):
    return MediaImage.objects.create(
        image=SimpleUploadedFile(name, data or _png()),
        title=title,
        alt_en="alt en",
        alt_de="alt de",
        **kw,
    )


def test_media_image_reencoded_hashed_and_named(media_root, fake_pipeline):
    page = make_page("mein-event")
    img = _make_image("Größe", first_used_on=page)
    year = timezone.localdate().year
    assert img.image.name == f"website/{year}/mein-event-groesse.png"
    stored = (media_root / img.image.name).read_bytes()
    assert stored == b"REENCODED-PNG"
    assert img.sha256 == hashlib.sha256(stored).hexdigest()
    assert fake_pipeline.calls == ["PNG"]
    assert img.markdown_snippet("de") == f"![alt de](/media/{img.image.name})"
    assert img.alt_for("en") == "alt en"


def test_media_image_collision_numbered(media_root):
    a = _make_image("Same")
    b = _make_image("Same")
    c = _make_image("Same")
    assert [i.image.name.rsplit("/", 1)[1] for i in (a, b, c)] == [
        "same.png",
        "same-2.png",
        "same-3.png",
    ]


def test_media_image_invalid_not_stored(media_root, fake_pipeline):
    with pytest.raises(ValidationError):
        _make_image(name="x.jpg", data=_png())
    assert MediaImage.objects.count() == 0
    assert fake_pipeline.calls == []


def test_media_image_resave_keeps_file_and_hash(media_root, fake_pipeline):
    img = _make_image("Keep")
    name, sha = img.image.name, img.sha256
    img.title = "Changed"
    img.save()
    assert img.image.name == name and img.sha256 == sha
    assert fake_pipeline.calls == ["PNG"]


def test_media_image_requires_both_alts():
    img = MediaImage(title="t")
    with pytest.raises(ValidationError) as exc:
        img.full_clean()
    assert "alt_en" in exc.value.message_dict and "alt_de" in exc.value.message_dict


def test_cover_image_protected(media_root):
    img = _make_image("Cover")
    make_page("withcover", cover_image=img)
    from django.db.models import ProtectedError

    with pytest.raises(ProtectedError):
        img.delete()


@pytest.mark.parametrize(
    "alt, expected",
    [
        ("plain", "plain"),
        ("a [b] c", "a \\[b\\] c"),
        ("back\\slash", "back\\\\slash"),
        ("line one\nline two\r\n\r\nthree", "line one line two three"),
    ],
)
def test_markdown_snippet_escapes_alt(media_root, fake_pipeline, alt, expected):
    img = _make_image("Snippet", first_used_on=make_page("snip-page"))
    img.alt_en = alt
    assert img.markdown_snippet("en") == f"![{expected}](/media/{img.image.name})"
