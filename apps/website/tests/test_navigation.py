import pytest
from django.template import Context, Template
from pages.models import EventCategory, MediaImage
from website.navigation import alternate_language_path, build_nav, to_roman
from website.strings import _STRINGS, get_strings
from website.tests.utils import make_page

pytestmark = pytest.mark.django_db


@pytest.fixture
def site_tree():
    make_page("home", page_type="home")
    folder = make_page(
        "arbeitsfelder", page_type="folder", title="Working Fields", show_in_menu=True, menu_order=1
    )
    make_page(
        "qualitaet",
        page_type="work_field",
        title="Quality",
        parent=folder,
        show_in_menu=True,
        menu_order=1,
    )
    make_page(
        "kommunikation",
        page_type="work_field",
        title="Communication",
        parent=folder,
        show_in_menu=True,
        menu_order=2,
    )
    make_page(
        "hidden",
        page_type="work_field",
        title="Hidden",
        parent=folder,
        show_in_menu=False,
        menu_order=3,
    )
    make_page(
        "draft",
        page_type="work_field",
        title="Draft",
        parent=folder,
        show_in_menu=True,
        is_published=False,
        menu_order=4,
    )
    about = make_page(
        "impressum", page_type="folder", title="About", show_in_menu=True, menu_order=2
    )
    make_page(
        "privacy", page_type="legal", title="Imprint", parent=about, show_in_menu=True, menu_order=1
    )
    make_page("events", page_type="event_list", title="Events", show_in_menu=True, menu_order=3)
    make_page("news", page_type="article_list", title="News", show_in_menu=True, menu_order=4)
    make_page(
        "secret", page_type="article_list", title="Secret", show_in_menu=True, is_published=False
    )
    make_page(
        "other", page_type="article_list", title="Other language", language="de", show_in_menu=True
    )
    return folder


def test_to_roman():
    assert [to_roman(n) for n in (1, 2, 4, 5, 9, 14)] == ["I", "II", "IV", "V", "IX", "XIV"]
    assert (
        to_roman(0) == "" and to_roman("x") == "" and to_roman(None) == "" and to_roman(4000) == ""
    )


def test_build_nav_structure(site_tree):
    nav = build_nav("en")
    assert [i["title"] for i in nav["items"]] == ["Working Fields", "About", "Events", "News"]
    working = nav["items"][0]
    assert [c["title"] for c in working["children"]] == ["I: Quality", "II: Communication"]
    assert working["url"] == "/en/arbeitsfelder"
    assert working["children"][0]["url"] == "/en/arbeitsfelder/qualitaet"
    assert [i["submenu_index"] for i in nav["items"]] == [1, 2, 0, 0]
    assert [p.title for p in nav["work_fields"]] == ["Quality", "Communication", "Hidden"]
    assert [p.title for p in nav["legal_pages"]] == ["Imprint"]
    assert nav["news_url"] == "/en/news"


def test_build_nav_is_language_specific(site_tree):
    assert [i["title"] for i in build_nav("de")["items"]] == ["Other language"]


def test_build_nav_skips_pages_below_unpublished_folder(site_tree):
    site_tree.is_published = False
    site_tree.save()
    nav = build_nav("en")
    assert [i["title"] for i in nav["items"]] == ["About", "Events", "News"]
    assert nav["work_fields"] == []


def test_build_nav_query_count(site_tree, django_assert_max_num_queries):
    with django_assert_max_num_queries(2):
        nav = build_nav("en")
        for item in nav["items"]:
            assert item["url"]
            for child in item["children"]:
                assert child["url"]
        for page in nav["work_fields"] + nav["legal_pages"]:
            assert page.nav_url


def test_alternate_language_path(site_tree):
    en_wf = site_tree.children.get(slug="qualitaet")
    # no counterpart yet -> other-language home
    assert alternate_language_path(en_wf, "en") == "/de"
    de_folder = make_page("arbeitsfelder", language="de", page_type="folder")
    make_page("qualitaet", language="de", page_type="work_field", parent=de_folder)
    assert alternate_language_path(en_wf, "en") == "/de/arbeitsfelder/qualitaet"


def test_alternate_language_path_requires_published_counterpart_chain(site_tree):
    en_wf = site_tree.children.get(slug="qualitaet")
    de_folder = make_page("arbeitsfelder", language="de", page_type="folder", is_published=False)
    make_page("qualitaet", language="de", page_type="work_field", parent=de_folder)
    assert alternate_language_path(en_wf, "en") == "/de"


def test_alternate_language_path_home_and_missing_page(site_tree):
    home = make_page("start", language="de", page_type="home")
    assert alternate_language_path(home, "de") == "/en"
    assert alternate_language_path(None, "en") == "/de"


def test_alt_and_catname_filters_use_language():
    image = MediaImage(alt_en="A cat", alt_de="Eine Katze")
    category = EventCategory(name_en="Workshop", name_de="Werkstatt")
    template = Template("{% load website_tags %}{{ img|alt:lang }}|{{ cat|catname:lang }}")
    assert (
        template.render(Context({"img": image, "cat": category, "lang": "de"}))
        == "Eine Katze|Werkstatt"
    )
    assert (
        template.render(Context({"img": image, "cat": category, "lang": "en"})) == "A cat|Workshop"
    )
    assert template.render(Context({"img": None, "cat": None, "lang": "de"})) == "|"


def test_roman_and_public_url_filters(site_tree, settings):
    settings.WEBSITE_PUBLIC_URL = "https://dalia.education/"
    page = site_tree.children.get(slug="qualitaet")
    rendered = Template(
        "{% load website_tags %}{{ n|roman }} {{ page|public_url }} {{ '/en'|public_url }}"
    ).render(Context({"n": 3, "page": page}))
    assert (
        rendered
        == "III https://dalia.education/en/arbeitsfelder/qualitaet https://dalia.education/en"
    )


def test_icon_arrow_tag_sanitises_parameters():
    html = Template(
        "{% load website_tags %}{% icon_arrow width=13 height=bad rotate=180 fill=evil %}"
    ).render(Context({"bad": "x", "evil": '"><script>'}))
    assert 'width="13"' in html and 'height="15"' in html
    assert "rotate(180deg)" in html
    assert "<script>" not in html and 'fill="#000050"' in html


def test_strings_have_same_keys_in_both_languages():
    assert set(_STRINGS["en"]) == set(_STRINGS["de"])
    required = {
        "home_title",
        "working_fields",
        "keep_reading",
        "more_information",
        "authors",
        "past_event",
        "footer_subscribe",
        "follow_us",
        "partner_names",
        "lang_de",
        "lang_en",
        "contact_submit",
    }
    assert required <= set(_STRINGS["en"])


def test_get_strings_language_and_fallback():
    assert get_strings("de")["home_title"] == "Startseite"
    assert get_strings("fr")["home_title"] == "Home"
    assert get_strings("de")["past_event"] == "Vergangene Veranstaltung"
    strings = get_strings("en")
    strings["partner_names"].append("x")
    assert "x" not in get_strings("en")["partner_names"]


def test_build_nav_newsletter_url_per_language():
    make_page("home", page_type="home")
    make_page("newsletter", page_type="article_list", title="Newsletter")
    make_page(
        "newsletter",
        language="de",
        page_type="article_list",
        title="Newsletter",
        is_published=False,
    )
    assert build_nav("en")["newsletter_url"] == "/en/newsletter"
    assert build_nav("de")["newsletter_url"] == ""
