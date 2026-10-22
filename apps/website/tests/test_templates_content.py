"""Template tests for the legal, event_list, article_list, article and event page types (slice S9)."""

import datetime
import io
import re

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from pages.models import EventCategory, MediaImage, Page, PageBlock
from PIL import Image
from website.tests.utils import (
    make_page,
    parse_html,
    select,
    select_one,
    site_get,
    text_of,
    website_client,
)

pytestmark = pytest.mark.django_db

EVIL = "\"'</script><img src=x onerror=alert(1)>"


@pytest.fixture
def client(settings):
    return website_client(settings)


@pytest.fixture
def media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)


def _image(title="cover"):
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(buf, "PNG")
    upload = SimpleUploadedFile(f"{title}.png", buf.getvalue(), content_type="image/png")
    return MediaImage.objects.create(
        image=upload, title=title, alt_en="English alt", alt_de="Deutscher Alt"
    )


def _set_html(page, html):
    Page.objects.filter(pk=page.pk).update(content_html=html)


def _content(response):
    """Page-specific markup: everything between the header and the footer."""
    body = response.content.decode()
    return body.split("</nav>", 1)[-1].split('id="footer"', 1)[0]


def _get(client, page):
    response = site_get(client, page.get_public_path())
    assert response.status_code == 200
    return response, parse_html(response.content)


# -- legal -----------------------------------------------------------------


def test_legal_sidebar_and_privacy_text(client):
    make_page("home", page_type="home", title="")
    legal = make_page("privacy", page_type="legal", title="Privacy Policy")
    make_page("imprint", page_type="legal", title="Imprint")
    _set_html(legal, "<h3>Publisher</h3><p>Text</p>")
    response, root = _get(client, legal)
    assert select_one(root, ".col-md-2.p-0.mobile-hide .bordered-content.no-right-border")
    sidebar = " ".join(a.text() for a in select(root, ".col-md-2 a.light"))
    assert "Privacy Policy" in sidebar and "Imprint" in sidebar
    assert text_of(root, ".imprint-margin h1.mt-0") == "Privacy Policy"
    assert "Publisher" in text_of(root, "#privacy_text")
    assert select_one(root, "#header.desktop-hide-2")
    assert not select_one(root, "nav#header-container")  # no top navigation


# -- event list -------------------------------------------------------------


@pytest.fixture
def event_tree():
    make_page("home", page_type="home", title="")
    listing = make_page("events", page_type="event_list", title="Events")
    cat = EventCategory.objects.create(name_en="Workshops", name_de="Werkstätten", color="#FF7B42")
    today = timezone.localdate()
    past = make_page(
        "old",
        page_type="event",
        title="Old Event",
        parent=listing,
        date=today - datetime.timedelta(days=30),
        location="Aachen",
        time_text="10:00 - 12:00",
        category=cat,
        summary="Past summary",
    )
    future = make_page(
        "new",
        page_type="event",
        title="New Event",
        parent=listing,
        date=today + datetime.timedelta(days=30),
        summary="",
    )
    _set_html(future, "<p>" + "word " * 40 + "</p>")
    return listing, past, future, cat


def test_event_list_order_badge_category_and_colour(client, event_tree):
    listing, past, future, cat = event_tree
    _, root = _get(client, listing)
    rows = select(root, ".single-event")
    assert len(rows) == 2
    assert text_of(rows[0], "h3") == "New Event"  # date descending
    assert text_of(rows[1], "h3") == "Old Event"
    assert not select(rows[0], ".white-bg-box")
    assert text_of(rows[1], ".white-bg-box") == "Past Event"
    assert text_of(rows[1], "p.m-0") == "Workshops"
    assert text_of(rows[0], ".col-md-3.pl-0 p.m-0") == ""
    button = select_one(rows[1], "button.btn.btn-primary.height-50.mobile-button")
    assert button.attrs["style"] == "background-color: #FF7B42"
    assert "btn-back" not in " ".join(button.classes)
    assert select_one(rows[1], "a.buttonlink").attrs["href"] == "/en/events/old"
    no_cat = select_one(rows[0], "button.btn-primary")
    assert "style" not in no_cat.attrs
    assert text_of(rows[1], ".col-md-4 p") == "Past summary"
    details = text_of(rows[0], ".col-md-4 p")
    assert details.endswith("…") and len(details) == 80
    assert text_of(root, ".single-event-heading .col-md-3.pl-0 p") == "Event"


def test_event_list_german_labels_and_no_onclick(client, event_tree):
    listing, *_ = event_tree
    home_de = make_page("home", language="de", page_type="home", title="")
    assert home_de
    de_list = make_page("veranstaltungen", language="de", page_type="event_list", title="Events")
    cat = EventCategory.objects.get()
    past = make_page(
        "alt",
        language="de",
        page_type="event",
        title="Altes Event",
        parent=de_list,
        date=datetime.date(2020, 1, 1),
        category=cat,
    )
    assert past
    response, root = _get(client, de_list)
    assert text_of(root, ".white-bg-box") == "Vergangene Veranstaltung"
    assert text_of(root, "#events-section a.buttonlink").startswith("Eventseite")
    assert text_of(root, ".single-event .col-md-3.pl-0 p.m-0") == "Werkstätten"
    assert "onclick" not in _content(response)


def test_event_list_english_button_label(client, event_tree):
    listing, *_ = event_tree
    _, root = _get(client, listing)
    assert text_of(root, "#events-section a.buttonlink").startswith("Event page")


def test_event_list_escapes_editor_text(client, event_tree):
    listing, past, *_ = event_tree
    Page.objects.filter(pk=past.pk).update(title=EVIL, location=EVIL)
    response, _ = _get(client, listing)
    section = _content(response)
    assert "<img src=x" not in section
    assert "onclick" not in section


# -- event detail -------------------------------------------------------------


def test_event_detail_sections_address_agenda(client, event_tree, media):
    listing, past, *_ = event_tree
    image = _image()
    Page.objects.filter(pk=past.pk).update(
        cover_image=image,
        address="Building 2020\nLandoltweg 1a\n52074 Aachen",
        date_text="25.08.2025",
    )
    PageBlock.objects.create(page=past, kind="section", label="Speaker", body_md="Some **text**")
    PageBlock.objects.create(page=past, kind="section", label="Info", body_md="Free")
    PageBlock.objects.create(
        page=past,
        kind="agenda",
        sort_order=1,
        label="10:00 – 10:30",
        title="Welcome",
    )
    PageBlock.objects.create(
        page=past,
        kind="agenda",
        sort_order=2,
        label="10:30 – 13:00",
        title="Session 1",
        body_md="10:30 Talk A\n\n11:00 Talk <b>B</b>",
    )
    response, root = _get(client, past)
    back = select_one(root, "p.mt-25 a.light")
    assert back.attrs["href"] == "/en/events" and back.text() == "Back"
    assert text_of(root, "h1.mt-0.sixty-width") == "Old Event"
    assert text_of(root, ".white-bg-box") == "Past Event"
    assert select_one(root, ".row.mt-5 .col-md-7 p.m-0").text() == "Workshops"
    assert [h.text() for h in select(root, ".col-md-5.px-0 h3")] == [
        "Aachen",
        "25.08.2025",
        "10:00 - 12:00",
    ]
    labels = [h.text() for h in select(root, ".col-md-7.px-0 h6")]
    assert labels == ["Speaker", "Info"]
    assert len(select(root, "p.w-75.mt-2")) == 2
    img = select_one(root, ".width-50 img.width-100")
    assert img.attrs["alt"] == "English alt" and img.attrs["src"].startswith("/media/")
    lines = select(root, ".width-50.mt-4 p")
    assert [p.text() for p in lines] == ["Building 2020", "Landoltweg 1a", "52074 Aachen"]
    assert lines[0].classes == ["mt-2", "mb-0"] and lines[1].classes == ["m-0"]
    assert text_of(root, ".width-50.mt-4 h6") == "Address"
    items = select(root, "ul.pl-4 > li")
    assert len(items) == 2
    assert text_of(items[0], "strong") == "10:00 – 10:30:"
    assert not select(items[0], "ul.schedule-list")
    subs = select(items[1], "ul.schedule-list > li > p")
    assert [s.text() for s in subs] == ["10:30 Talk A", "11:00 Talk <b>B</b>"]
    assert "<b>B</b>" not in response.content.decode()
    assert "onclick" not in _content(response)


def test_event_detail_without_agenda_and_in_german(client, event_tree):
    make_page("home", language="de", page_type="home", title="")
    de_list = make_page("veranstaltungen", language="de", page_type="event_list", title="Events")
    event = make_page(
        "alt",
        language="de",
        page_type="event",
        title="Altes Event",
        parent=de_list,
        date=datetime.date(2020, 1, 1),
    )
    response, root = _get(client, event)
    assert select_one(root, "p.mt-25 a.light").attrs["href"] == "/de/veranstaltungen"
    assert select_one(root, "p.mt-25 a.light").text() == "Zurück"
    assert text_of(root, ".white-bg-box") == "Vergangene Veranstaltung"
    assert not select(root, "ul.pl-4")
    assert "Agenda" not in _content(response)


def test_event_today_is_not_past(client, event_tree):
    listing, *_ = event_tree
    event = make_page(
        "today",
        page_type="event",
        title="Today",
        parent=listing,
        date=timezone.localdate() - datetime.timedelta(days=1),
        date_end=timezone.localdate(),
    )
    _, root = _get(client, event)
    assert not select(root, ".white-bg-box")


# -- article list ---------------------------------------------------------------


@pytest.fixture
def news_tree(media):
    make_page("home", page_type="home", title="")
    make_page("home", language="de", page_type="home", title="")
    news = make_page("news", page_type="article_list", title="News")
    image = _image("news")
    a1 = make_page(
        "a1",
        page_type="article",
        title="First",
        parent=news,
        date=datetime.date(2025, 10, 28),
        summary="Teaser one",
        cover_image=image,
        authors="Jane Doe",
    )
    a2 = make_page(
        "a2",
        page_type="article",
        title="Second",
        parent=news,
        date=datetime.date(2026, 5, 5),
        summary="",
    )
    _set_html(a2, "<p>Fallback &amp; text</p>")
    _set_html(a1, "<p>Body one</p><p>Body two</p>")
    return news, a1, a2, image


def test_article_list_desktop_and_mobile_blocks(client, news_tree):
    news, a1, a2, image = news_tree
    _, root = _get(client, news)
    assert text_of(root, "#news-section h1.feature-heading.full-width") == "News"
    desktop = select_one(root, ".center-box.mobile-hide")
    mobile = select_one(root, ".center-box.desktop-hide.news-mobile")
    d_articles = select(desktop, ".article.mb-4")
    m_articles = select(mobile, ".article.mb-4")
    assert [text_of(a, "h2 a.a-title") for a in d_articles] == ["Second", "First"]
    assert [text_of(a, "h2 a.a-title") for a in m_articles] == ["Second", "First"]
    assert select_one(d_articles[1], ".pr-2.width-35 a img.width-100").attrs["alt"] == "English alt"
    assert select_one(m_articles[1], ".width-100 a img.width-100").attrs["alt"] == "English alt"
    assert not select(d_articles[0], "img")
    assert select_one(d_articles[1], ".flex.flex-row.padding-tb")
    assert select_one(m_articles[1], ".flex.flex-column.padding-tb")
    assert select_one(m_articles[1], "p.text-justify").text() == "Teaser one"
    assert text_of(d_articles[0], ".width-65 p") == "Fallback & text"
    link = select_one(d_articles[1], "button.btn.btn-primary a.buttonlink")
    assert link.attrs["href"] == "/en/news/a1" and link.text() == "More"
    assert not select(root, ".center-box.border-bottom")  # no intro without body


def test_article_list_intro_and_german_alt(client, news_tree):
    news, a1, a2, image = news_tree
    _set_html(news, "<p>Intro text</p>")
    _, root = _get(client, news)
    assert text_of(root, ".center-box.border-bottom") == "Intro text"
    de_news = make_page("neuigkeiten", language="de", page_type="article_list", title="News")
    make_page(
        "de1", language="de", page_type="article", title="Eins", parent=de_news, cover_image=image
    )
    _, root = _get(client, de_news)
    assert select_one(root, ".article img").attrs["alt"] == "Deutscher Alt"
    assert text_of(root, ".article button a.buttonlink") == "Mehr"


def test_article_list_unpublished_child_hidden_and_undated_by_menu_order(client, news_tree):
    news, a1, a2, _ = news_tree
    Page.objects.filter(pk__in=[a1.pk, a2.pk]).update(date=None)
    Page.objects.filter(pk=a1.pk).update(menu_order=2)
    Page.objects.filter(pk=a2.pk).update(menu_order=1, is_published=False)
    _, root = _get(client, news)
    assert [
        text_of(a, "h2 a.a-title") for a in select(root, ".center-box.mobile-hide .article")
    ] == ["First"]


def test_article_list_title_truncated_and_escaped(client, news_tree):
    news, a1, *_ = news_tree
    Page.objects.filter(pk=a1.pk).update(title="T" * 120 + EVIL)
    response, root = _get(client, news)
    title = text_of(root, ".center-box.mobile-hide h2 a.a-title")
    assert len(title) <= 80 or title.startswith("Second")
    assert "<img src=x" not in response.content.decode()


# -- article detail -----------------------------------------------------------------


def test_article_detail_authors_date_two_bodies(client, news_tree):
    news, a1, *_ = news_tree
    response, root = _get(client, a1)
    desktop = select_one(root, "article.center-box.mobile-hide")
    mobile = select_one(root, "article.center-box.desktop-hide.flex-column")
    for block in (desktop, mobile):
        assert text_of(block, ".title-center h1.mt-0") == "First"
        assert text_of(block, "h4.text-decoration-ul") == "Authors"
        assert text_of(block, "p.text-left.mt-0") == "Jane Doe"
        assert text_of(block, "p.text-right") == "28.10.2025"
        assert "Body one" in text_of(block, ".post-content")
    assert select_one(mobile, ".flex.flex-row.border-bottom.mt-2-mobile")
    assert select_one(mobile, ".title-center.mt-4-5")


def test_article_detail_german_labels(client, news_tree):
    de_news = make_page("neuigkeiten", language="de", page_type="article_list", title="News")
    art = make_page("eins", language="de", page_type="article", title="Eins", parent=de_news)
    _, root = _get(client, art)
    assert [h.text() for h in select(root, "h4.text-decoration-ul")] == ["Autoren", "Autoren"]


def test_bare_email_in_body_is_mailto_link(client, news_tree):
    news, a1, *_ = news_tree
    a1.content_md = "Write to info@example.org please"
    a1.save()
    a1.refresh_from_db()
    _, root = _get(client, a1)
    link = select_one(root, ".post-content a")
    assert link is not None and link.attrs["href"] == "mailto:info@example.org"


# -- CSP: no inline scripts or event-handler attributes ----------------------

INLINE_SCRIPT = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>", re.I)
INLINE_HANDLER = re.compile(r"<[a-z][^>]*\son[a-z]+\s*=", re.I)


def _assert_clean(client, pages):
    for page in pages:
        html = _get(client, page)[0].content.decode()
        assert not INLINE_SCRIPT.search(html), page.slug
        assert not INLINE_HANDLER.search(html), page.slug


def test_event_pages_have_no_inline_scripts_or_handlers(client, event_tree):
    listing, past, future, _cat = event_tree
    _assert_clean(client, [listing, past, future])


def test_article_pages_have_no_inline_scripts_or_handlers(client, news_tree):
    news, a1, a2, _image_ = news_tree
    _assert_clean(client, [news, a1, a2])
