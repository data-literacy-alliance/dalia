"""Tests for the Grav site importer (synthetic fixtures only, no dependency on the real source)."""

import datetime as dt
from io import StringIO

import pytest
from django.core.management import call_command
from pages.models import EventCategory, MediaImage, Page
from PIL import Image
from website import grav_snapshot as snap
from website.grav_import import (
    Converter,
    convert_grav_markdown,
    decode_js_string,
    fragment_to_markdown,
    js_call_strings,
    parse_date_text,
    parse_html,
    select,
    select_one,
    select_text,
    split_front_matter,
    strip_leading_heading,
    strip_order_prefix,
)

# -- html tree and selectors ------------------------------------------------------


def test_select_matches_descendants_by_tag_class_and_id():
    root = parse_html(
        '<div id="a" class="x y"><p class="m">one</p><section><p class="m">two</p></section></div>'
    )
    assert [n.text() for n in select(root, "div#a p.m")] == ["one", "two"]
    assert select_text(root, "div.x.y section p") == "two"
    assert select_one(root, "div.missing") is None


def test_nested_paragraphs_are_closed_like_a_browser():
    root = parse_html('<p class="w"><p>text</p></p><h2>h</h2>')
    assert [n.text() for n in select(root, "p")] == ["", "text"]
    assert select_text(root, "h2") == "h"


def test_script_and_svg_content_is_ignored_in_text():
    root = parse_html("<div>a<script>var x=1;</script><svg><path/></svg>b</div>")
    assert select_text(root, "div") == "ab"


# -- html to markdown -----------------------------------------------------------------


def convert(fragment, hook=None):
    warnings = []
    conv = Converter(image_hook=hook, warn=warnings.append)
    return fragment_to_markdown(fragment, conv), warnings


def test_markdown_paragraphs_links_emphasis_and_headings():
    md, _ = convert(
        '<h2>Title</h2><p>Hello <a href="https://e.org/a b">a <strong>link</strong></a> and '
        "<em>more</em>.</p>"
    )
    assert md == "## Title\n\nHello [a **link**](https://e.org/a%20b) and *more*."


def test_markdown_escapes_special_characters_and_block_starts():
    md, _ = convert("<p>1. Not a list *star* [x] $5</p><p>- dash</p>")
    assert md == "1\\. Not a list \\*star\\* \\[x\\] \\$5\n\n\\- dash"


def test_markdown_lists_with_nested_list_and_paragraph_items():
    md, _ = convert("<ul><li>a<ul><li>b</li></ul></li><li><p>c</p></li></ul><ol><li>x</li></ol>")
    assert md == "- a\n    - b\n- c\n\n1. x"


def test_markdown_line_break_and_blockquote():
    md, _ = convert("<p>a<br>b</p><blockquote><p>q</p></blockquote>")
    assert md == "a\\\nb\n\n> q"


def test_images_use_hook_and_unavailable_images_are_dropped_with_caption():
    html = '<figure><img src="/x.png" alt="Alt"><figcaption>Cap</figcaption></figure>'
    md, warnings = convert(html, hook=lambda src, alt, title: "/media/x.png")
    assert md == "![Alt](/media/x.png)\n\n*Cap*"
    md, warnings = convert(html)
    assert md == "" and len(warnings) == 1


def test_javascript_string_decoding():
    assert decode_js_string(r"Work\u0020Package\u00205") == "Work Package 5"
    call = r"updateContent('A\u0020B', 'it\'s', '\u003Cp\u003Ex\u003C\/p\u003E')"
    assert js_call_strings(call) == ["A B", "it's", "<p>x</p>"]
    assert fragment_to_markdown(js_call_strings(call)[2]) == "x"


# -- grav source -------------------------------------------------------------------------


def test_front_matter_split_and_broken_yaml_warning():
    front, body = split_front_matter("---\ntitle: T\nlist:\n  - a\n---\n\nBody")
    assert front == {"title": "T", "list": ["a"]} and body.strip() == "Body"
    warnings = []
    front, _ = split_front_matter("---\nkey: [unclosed\n---\ntext", warnings.append)
    assert front == {} and warnings
    assert split_front_matter("no front matter")[0] == {}


def test_grav_markdown_drops_twig_shortcodes_and_resolves_images():
    requested, warnings = [], []
    conv = Converter(image_hook=lambda src, alt, title: requested.append(src), warn=warnings.append)
    text = (
        "# Heading\n\n{{ page.title }} [notice=info]Careful[/notice] "
        "line<br>break ![pic](img.png?cropZoom=1,1) [kept](https://e.org)"
    )
    out = convert_grav_markdown(text, conv)
    assert "{{" not in out and "[notice" not in out and "[/notice" not in out
    assert "![pic]" not in out and "[kept](https://e.org)" in out
    assert "line\\\nbreak" in out
    assert requested == ["img.png?cropZoom=1,1"]
    assert any("Twig" in w for w in warnings) and any("shortcode" in w for w in warnings)
    assert any("image dropped" in w for w in warnings)


def test_helpers_for_names_and_headings():
    assert strip_order_prefix("02.arbeitsfelder") == "arbeitsfelder"
    assert strip_order_prefix("20240612_open_horizons") == "20240612_open_horizons"
    assert strip_leading_heading("\n# Title\n\ntext") == "text"


@pytest.mark.parametrize(
    "text,start,end,free",
    [
        ("12.06.2024", dt.date(2024, 6, 12), None, ""),
        ("04. - 05.09.2025", dt.date(2025, 9, 4), dt.date(2025, 9, 5), ""),
        ("31.01. - 01.02.2024", dt.date(2024, 1, 31), dt.date(2024, 2, 1), ""),
        ("01.12.2024 - 03.01.2025", dt.date(2024, 12, 1), dt.date(2025, 1, 3), ""),
        ("am 12.06.2024 online", dt.date(2024, 6, 12), None, "am 12.06.2024 online"),
        ("sometime", None, None, "sometime"),
    ],
)
def test_parse_date_text(text, start, end, free):
    assert parse_date_text(text) == (start, end, free)


# -- snapshot extractors -------------------------------------------------------------------

EVENT_HTML = """
<div class="row mt-5"><div class="col-md-7"><p class="m-0">Series</p><h1>Event title</h1>
<p class="m-0 white-bg-box">Past</p></div>
<div class="col-md-5"><h3>Mainz</h3><h3>04. - 05.09.2025</h3><h3>10:00 - 11:00</h3></div></div>
<div class="py-5"><div class="col-md-7 px-0"><h6></h6><p class="w-75"><p>Intro text.</p></p>
<h6>Speaker</h6><p class="w-75"><p>Somebody</p></p></div>
<div class="width-50 mt-4"><h6>Address</h6><p>Line one</p><p>Line two</p></div></div>
<ul class="pl-4"><li><strong>10:00 - 10:30:</strong> Welcome
<ul class="schedule-list"><li><p>First</p></li></ul></li></ul>
"""


def test_extract_event_sections_agenda_and_address():
    data = snap.extract_event(parse_html(EVENT_HTML), Converter())
    assert data["category"] == "Series" and data["title"] == "Event title"
    assert (data["location"], data["date_text"], data["time_text"]) == (
        "Mainz",
        "04. - 05.09.2025",
        "10:00 - 11:00",
    )
    assert data["sections"] == [
        {"label": "", "body": "Intro text."},
        {"label": "Speaker", "body": "Somebody"},
    ]
    assert data["address_lines"] == ["Line one", "Line two"]
    assert data["agenda"] == [{"label": "10:00 - 10:30", "title": "Welcome", "lines": ["First"]}]


def test_extract_work_field_decodes_package_bodies_from_onclick():
    html = (
        '<section class="hero-section-2"><img class="mobile-icon" src="/i.png">'
        '<h1>Working Field II X</h1><p class="text-block">Hero</p></section>'
        '<div id="myTab"><a class="nav-link" onclick="updateContent(\'WP\\u00205\', \'T\', '
        '\'Body\\u0020text\')"><p class="hover-white">WP 5</p>'
        '<h5 class="tabheading">T</h5></a></div>'
    )
    data = snap.extract_work_field(parse_html(html), Converter())
    assert data["icon"] == "/i.png" and data["summary"] == "Hero"
    assert data["packages"] == [{"label": "WP 5", "title": "T", "body": "Body text"}]


def test_extract_article_list_and_article():
    listing = (
        '<section id="news-section"><h1 class="feature-heading">News</h1>'
        '<div class="center-box mobile-hide"><div class="article"><img src="/a.jpg" alt="A">'
        '<div class="width-65"><h2><a href="/en/news/item_1">First</a></h2><p>Teaser</p></div>'
        "</div></div></section>"
    )
    data = snap.extract_article_list(parse_html(listing), Converter())
    assert data["title"] == "News" and data["items"][0]["slug"] == "item_1"
    assert data["items"][0]["summary"] == "Teaser"
    article = (
        '<article class="center-box"><h1>T</h1><p class="text-left">Me</p>'
        '<p class="text-right">28.10.2025</p><div class="post-content"><p>Body</p></div></article>'
    )
    data = snap.extract_article(parse_html(article), Converter())
    assert (data["title"], data["authors"], data["date_text"], data["body"]) == (
        "T",
        "Me",
        "28.10.2025",
        "Body",
    )


def test_extractors_reject_unknown_structure():
    with pytest.raises(ValueError):
        snap.extract_legal(parse_html("<p>x</p>"), Converter())


# -- command ---------------------------------------------------------------------------------

HOME_HTML = """<html><head><link rel="canonical" href="http://dalia.education/{lang}" /></head><body>
<div class="navbar-nav mobile-hide"><ul>
<li><a href="/{lang}/impressum">Imprint folder</a></li>
<li><a href="/{lang}/arbeitsfelder">Fields folder</a></li></ul></div>
<div class="hero-section"><h5 class="custom-h5">Hi</h5><h5 class="quote">Quote</h5></div>
<section id="features-section"><div class="feature-heading"><h4>M</h4><h1>Mission</h1>
<p class="text-block"><p>Mission body</p></p></div>
<div class="feature-box"><h3>Field A</h3><p class="mobile-hide">Card A</p></div></section>
<section id="nfdi-section"><div class="content"><h4>N</h4><h2>Nfdi</h2><p>Body</p></div>
<div class="feature-box"><h3>C1</h3><a class="read-more-link" href="https://e.org/1">more</a></div></section>
<section id="partner-section"><div class="pright-5"><h4>P</h4><h2>Partners</h2><p>Text</p></div>
<div class="mobile-hide"><h4>Our</h4><a href="https://e.org/p"><img src="/user/themes/dalia/images/p/logo.png" alt="Logo P"></a>
<h4>Funders</h4></div></section></body></html>"""

LEGAL_HTML = """<html><head><link rel="canonical" href="http://dalia.education/en/impressum/privacy" />
</head><body><div class="imprint-margin"><h1>Imprint</h1></div>
<div id="privacy_text"><p><h2>Part</h2><p>Legal <a href="mailto:a@b.org">a@b.org</a></p></div></body></html>"""


@pytest.fixture
def grav_tree(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    pages = tmp_path / "grav" / "pages"
    theme = tmp_path / "grav" / "themes" / "dalia"
    html = tmp_path / "html"
    (theme / "images" / "p").mkdir(parents=True)
    Image.new("RGB", (20, 10), (200, 10, 10)).save(theme / "images" / "p" / "logo.png")
    legal_dir = pages / "05.Impressum" / "01.privacy"
    legal_dir.mkdir(parents=True)
    (legal_dir / "privacy.de.md").write_text(
        "---\ntitle: Impressum\n---\n\n### Herausgeber\n\nText [Link](../02.data_policy)\n",
        encoding="utf-8",
    )
    html.mkdir()
    for lang in ("en", "de"):
        (html / f"{lang}.html").write_text(HOME_HTML.format(lang=lang), encoding="utf-8")
    (html / "en_impressum_privacy.html").write_text(LEGAL_HTML, encoding="utf-8")
    return pages, theme, html


def run_import(grav_tree, *extra):
    pages, theme, html = grav_tree
    out = StringIO()
    call_command(
        "import_grav_site",
        str(pages),
        "--themes",
        str(theme),
        "--html-dir",
        str(html),
        *extra,
        stdout=out,
    )
    return out.getvalue()


@pytest.mark.django_db
def test_import_creates_home_legal_pages_and_is_idempotent(grav_tree):
    run_import(grav_tree)
    home_en = Page.objects.get(site="website", language="en", page_type="home")
    assert home_en.is_published
    assert list(home_en.blocks.values_list("kind", flat=True)) == [
        "hero",
        "mission",
        "nfdi_intro",
        "link_card",
        "partners_intro",
        "partner_logo",
    ]
    assert MediaImage.objects.count() == 1
    legal_en = Page.objects.get(site="website", language="en", slug="privacy")
    assert legal_en.title == "Imprint" and "mailto:a@b.org" in legal_en.content_html
    assert legal_en.get_public_path() == "/en/impressum/privacy"
    legal_de = Page.objects.get(site="website", language="de", slug="privacy")
    assert legal_de.title == "Impressum"
    assert "/de/impressum/data_policy" in legal_de.content_md
    assert not Page.objects.filter(site="website", language="de", slug="data_policy").exists()
    before = Page.objects.count(), MediaImage.objects.count()

    second = run_import(grav_tree)
    assert (Page.objects.count(), MediaImage.objects.count()) == before
    assert "already exists" in second


@pytest.mark.django_db
def test_dry_run_saves_nothing_and_leaves_no_files(grav_tree, settings):
    output = run_import(grav_tree, "--dry-run")
    assert "dry run" in output
    assert not Page.objects.filter(site="website").exists()
    assert not MediaImage.objects.exists()
    media = list(__import__("pathlib").Path(settings.MEDIA_ROOT).rglob("*.png"))
    assert media == []


@pytest.mark.django_db
def test_import_never_changes_existing_pages_and_reports_missing_sources(grav_tree):
    existing = Page.objects.create(
        site="website",
        language="de",
        slug="privacy",
        title="Manual",
        page_type="legal",
        content_md="manual",
    )
    output = run_import(grav_tree)
    existing.refresh_from_db()
    assert existing.title == "Manual" and existing.content_md == "manual"
    assert "no source for this language" in output  # e.g. newsletter, use cases, accessibility
    assert not EventCategory.objects.exists()
