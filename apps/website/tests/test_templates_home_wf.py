"""Template tests for the home and work_field page types (slice S8)."""

import io
import re
from types import SimpleNamespace
from unittest import mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from pages.models import MediaImage, PageBlock
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
def client(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    return website_client(settings)


def _image(title="logo"):
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(buf, "PNG")
    upload = SimpleUploadedFile(f"{title}.png", buf.getvalue(), content_type="image/png")
    return MediaImage.objects.create(
        image=upload, title=title, alt_en=f"{title} alt", alt_de=f"{title} Alt DE"
    )


def _block(page, kind, order=0, **fields):
    return PageBlock.objects.create(page=page, kind=kind, sort_order=order, **fields)


def _get(client, path):
    response = site_get(client, path)
    assert response.status_code == 200
    return response, parse_html(response.content)


def _kids(node, tag, *classes):
    """Direct children of ``node`` with ``tag`` and all ``classes``."""
    return [c for c in node.children if c.tag == tag and all(k in c.classes for k in classes)]


# -- home --------------------------------------------------------------------


@pytest.fixture
def home_tree():
    home = make_page("home", page_type="home", title="")
    folder = make_page("arbeitsfelder", page_type="folder", title="Working Fields")
    wf1 = make_page(
        "quality",
        page_type="work_field",
        title="Quality",
        parent=folder,
        menu_order=1,
        summary="Quality summary",
    )
    wf2 = make_page(
        "communication",
        page_type="work_field",
        title="Communication",
        parent=folder,
        menu_order=2,
        summary="Comm summary",
    )
    return home, wf1, wf2


def test_home_hero_and_video_en(client, home_tree):
    home = home_tree[0]
    _block(home, "hero", title="DALIA,...?", body_md="Plain <quote>")
    _, root = _get(client, "/en")
    assert text_of(root, ".hero-section .hero-inner h5.custom-h5") == "DALIA,...?"
    assert text_of(root, ".hero-section h5.quote") == "Plain <quote>"
    video = select_one(root, ".hero-inner .align-self-center.width-65.mt-4 > video#video.width-100")
    assert video.attrs["controls"] and video.attrs["muted"]
    source = select_one(video, "source")
    assert source.attrs["src"].endswith("/website/videos/251014_explainity_dalia_en_4k_v02.mp4")
    tracks = select(video, "track")
    assert [t.attrs["srclang"] for t in tracks] == ["en", "de"]
    assert "default" in tracks[0].attrs and "default" not in tracks[1].attrs
    assert (
        tracks[0]
        .attrs["src"]
        .endswith("/website/videos/251009_Explainity_DALIA_EN_4k_Untertitel_v02.vtt")
    )
    assert (
        tracks[1]
        .attrs["src"]
        .endswith("/website/videos/251009_Explainity_DALIA_DE_4k_Untertitel_v01.vtt")
    )


def test_home_video_de_loads_both_tracks(client):
    make_page("home", language="de", page_type="home", title="")
    _, root = _get(client, "/de")
    source = select_one(root, "video#video source")
    assert source.attrs["src"].endswith("/website/videos/251008_explainity_dalia_de_4k_v03.mp4")
    tracks = select(root, "video#video track")
    assert [t.attrs["srclang"] for t in tracks] == ["en", "de"]


def test_home_mission_anchor_and_working_field_cards_link_to_pages(client, home_tree):
    home, wf1, wf2 = home_tree
    _block(
        home,
        "mission",
        label="MISSION & VISION",
        title="Data literacy",
        body_md="Mission text",
    )
    _, root = _get(client, "/en")
    heading = select_one(root, "section#features-section.py-5.my-5 .feature-heading#mission-vision")
    assert heading is not None
    assert text_of(heading, "h4") == "MISSION & VISION"
    assert text_of(heading, "h1.feature-heading.full-width") == "Data literacy"
    assert "Mission text" in heading.text() or "Mission text" in text_of(root, "#features-section")
    assert text_of(root, "#features-section .m-50 h4") == "Working Fields"
    cards = select(root, ".feature-boxes.mt-4.h-100 > .feature-box.border")
    assert len(cards) == 2
    hrefs = [a.attrs["href"] for c in cards for a in select(c, ".text-left.p-4 > a")]
    assert hrefs == [
        wf1.get_public_path(),
        wf1.get_public_path(),
        wf2.get_public_path(),
        wf2.get_public_path(),
    ]
    assert "" not in hrefs and "/en" not in hrefs
    assert text_of(cards[0], "h3") == "Quality"
    assert text_of(cards[0], "p.mobile-hide") == "Quality summary"
    assert text_of(cards[1], "a.read-more-link.desktop-hide") == "Keep reading"


def test_home_nfdi_link_cards_default_icons_and_custom_image(client, home_tree):
    home = home_tree[0]
    _block(home, "nfdi_intro", label="OUR CONNECTION", title="We are part of NFDI", body_md="Intro")
    for n in range(3):
        _block(home, "link_card", n, title=f"Card {n + 1}", url=f"https://example.org/{n + 1}")
    _, root = _get(client, "/en")
    assert text_of(root, "#nfdi-section .col-md-8 .content.sixty-width h2") == "We are part of NFDI"
    boxes = select(root, "#nfdi-section .col-md-4 > .feature-box.border.full-width")
    assert len(boxes) == 3
    assert [("mb-2" in b.classes) for b in boxes] == [True, True, False]
    icons = [select_one(b, "img.icon-spacing-2").attrs["src"] for b in boxes]
    assert [i.rsplit("/", 1)[-1].split(".")[0] for i in icons] == ["nfdi-1", "nfdi-2", "nfdi-3"]
    link = select_one(boxes[1], "a.read-more-link")
    assert link.attrs["href"] == "https://example.org/2"
    assert link.text().strip() == "More information"
    assert text_of(root, "#nfdi-section .col-md-4 h4") == "NFDI Resources"


def test_home_link_card_with_image_uses_img_with_alt(client, home_tree):
    home = home_tree[0]
    image = _image("icon")
    _block(home, "link_card", 0, title="Card", url="https://example.org", image=image)
    _, root = _get(client, "/en")
    img = select_one(root, "#nfdi-section .feature-box img.icon-spacing-2")
    assert img.attrs["src"] == image.image.url
    assert img.attrs["alt"] == "icon alt"


def test_home_partner_rows_chunked_and_padded(client, home_tree):
    home = home_tree[0]
    _block(home, "partners_intro", label="PARTNERS", title="Supporters", body_md="Text")
    for n in range(7):
        _block(
            home,
            "partner_logo",
            n,
            title=f"P{n}",
            url=f"https://p{n}.example.org/",
            image=_image(f"p{n}"),
            label="large" if n == 0 else "",
        )
    _, root = _get(client, "/en")
    right = select_one(root, "#partner-section .col-md-8.py-10.border-left.pleft-5.mobile-hide")
    rows = [r for r in select(right, ".row") if r.parent is right and r.parent.tag == "div"]
    partner_rows = rows[:3]
    assert [r.classes for r in partner_rows] == [
        ["row", "mb-3"],
        ["row", "mb-3", "d-none", "d-md-flex"],
        ["row", "mt-1", "d-none", "d-md-flex"],
    ]
    assert [len(_kids(r, "div", "col-md-4")) for r in partner_rows] == [3, 3, 3]
    assert [len(select(r, "img")) for r in partner_rows] == [3, 3, 1]
    assert select_one(partner_rows[0], "img").classes == ["img-fluid-lg"]
    assert select_one(partner_rows[1], "img").classes == ["img-fluid"]
    first_link = select_one(partner_rows[0], "a")
    assert first_link.attrs["href"] == "https://p0.example.org/"
    # mobile block: rows of two, last one padded
    mobile = select_one(root, "#partner-section .full-width.desktop-hide.block")
    mobile_rows = select(mobile, ".d-flex.full-width.mt-4")
    assert len(mobile_rows) == 4
    assert [
        len(_kids(r, "div", "half-width", "px-0", "d-flex", "justify-content-center"))
        for r in mobile_rows
    ] == [2, 2, 2, 2]
    assert text_of(root, "#partner-section .col-md-4.flex-column h2") == "Supporters"


def test_home_funders_rows_and_alt_per_language(client):
    for lang in ("en", "de"):
        home = make_page("home", language=lang, page_type="home", title="")
        _block(home, "partner_logo", 0, image=_image("tu"), url="https://tu.example.org/")
        _block(home, "funder_logo", 0, image=_image("eu"))
        _block(
            home, "funder_logo", 1, image=_image("bm"), label="large", url="https://bm.example.org/"
        )
    _, root = _get(client, "/en")
    assert text_of(root, "#partner-section h4.black") == "Our Partners"
    funders = select_one(root, "#partner-section .row.mb-3 > .col-md-6.px-0").parent
    imgs = select(funders, "img")
    assert [i.attrs["alt"] for i in imgs] == ["eu alt", "bm alt"]
    assert imgs[1].classes == ["img-fluid-lg"]
    assert len(_kids(funders, "div", "col-md-6", "px-0")) == 2
    assert "Our Funders" in root.text()
    _, root_de = _get(client, "/de")
    alts = [i.attrs["alt"] for i in select(root_de, "#partner-section img")]
    assert "tu Alt DE" in alts and "eu Alt DE" in alts and "tu alt" not in alts
    assert "Unsere Förderer" in root_de.text()


def test_home_contact_section_ids_and_enabled(client, home_tree):
    status = SimpleNamespace(available=True, reasons=())
    with mock.patch("website.contact.sending_status", return_value=status):
        _, root = _get(client, "/en")
    modular = select_one(root, "div.modular-row.form")
    assert select_one(modular, "section#contact-section")
    form = select_one(root, "form#contact-form")
    assert form.attrs["name"] == "contact-form"
    assert "disabled" not in select_one(form, "button[type=submit]").attrs


def test_home_contact_submit_disabled_when_unavailable(client, home_tree):
    status = SimpleNamespace(available=False, reasons=("no_provider",))
    with mock.patch("website.contact.sending_status", return_value=status):
        _, root = _get(client, "/en")
    button = select_one(root, "form#contact-form button[type=submit]")
    assert "disabled" in button.attrs
    assert button.attrs["aria-disabled"] == "true"
    assert "disabled" in button.classes
    assert button.attrs["title"]


def test_home_without_blocks_renders(client):
    make_page("home", page_type="home", title="")
    response, root = _get(client, "/en")
    assert select_one(root, "section#nfdi-section")
    assert select_one(root, "section#partner-section")
    assert "no-store" in response["Cache-Control"] or "max-age=0" in response["Cache-Control"]


# -- work field -------------------------------------------------------------


@pytest.fixture
def wf_page():
    make_page("home", page_type="home", title="")
    folder = make_page("arbeitsfelder", page_type="folder", title="Working Fields")
    wf = make_page(
        "kommunikation",
        page_type="work_field",
        title="Communication",
        parent=folder,
        menu_order=2,
        summary="The aim of working field II",
        cover_image=_image("comm"),
    )
    _block(
        wf, "work_package", 0, label="Work Package 5", title="Community", body_md="First **body**"
    )
    _block(wf, "work_package", 1, label="Work Package 6", title="Use Cases", body_md="Second body")
    _block(wf, "work_package", 2, label="Work Package 7", title="Public Relations", body_md="Third")
    return wf


def test_work_field_hero(client, wf_page):
    _, root = _get(client, wf_page.get_public_path())
    hero = select_one(root, "section.hero-section-2 > .container.h-100 > .row.h-100")
    assert text_of(hero, "h1") == "Working Field II Communication"
    assert text_of(hero, "p.text-block") == "The aim of working field II"
    mobile = select_one(hero, ".hero-content img.desktop-hide.mobile-icon")
    desktop = select_one(hero, ".col-md-6.mobile-hide img.mr-40")
    assert mobile.attrs["src"] == wf_page.cover_image.image.url == desktop.attrs["src"]
    assert desktop.attrs["width"] == "30%"
    assert mobile.attrs["alt"] == "comm alt"


def test_work_field_tabs_markup_and_no_onclick(client, wf_page):
    response, root = _get(client, wf_page.get_public_path())
    assert text_of(root, "section.section-50-50 h1.mt-0") == "Work Packages"
    tabs = select(root, "#myTab.nav.flex-column.custom-tabs.mt-5[role=tablist] > a.nav-link.d-flex")
    assert len(tabs) == 3
    assert [t.attrs["id"] for t in tabs] == ["tab1-tab", "tab2-tab", "tab3-tab"]
    assert [t.attrs["data-wp-body"] for t in tabs] == ["wp-body-1", "wp-body-2", "wp-body-3"]
    assert [t.attrs["href"] for t in tabs] == ["#tab1", "#tab2", "#tab3"]
    assert all(t.attrs["data-toggle"] == "tab" for t in tabs)
    assert "active" in tabs[0].classes and "mt-3" not in tabs[0].classes
    assert all("mt-3" in t.classes and "active" not in t.classes for t in tabs[1:])
    icons = [select_one(t, "svg") for t in tabs]
    assert icons[0].classes == ["fill-white", "hover-fill"]
    assert icons[1].classes == ["fill-blue", "hover-fill"]
    assert text_of(tabs[1], "p.hover-white") == "Work Package 6"
    assert text_of(tabs[1], "h5.tabheading.hover-white") == "Use Cases"
    nav = select_one(root, "#myTab")
    assert not any("onclick" in n.attrs for n in [nav, *nav.iter_descendants()])
    assert "updateContent" not in response.content.decode()


def test_work_field_first_package_server_side_and_templates(client, wf_page):
    _, root = _get(client, wf_page.get_public_path())
    pane = select_one(
        root,
        ".col-md-6.border-left.bg-white.pleft-5 > .tab-content#myTabContent > .tab-pane.fade.show.active#tab1",
    )
    assert text_of(pane, "h4#smallTitle.mt-0") == "Work Package 5"
    assert text_of(pane, "h2#mainTitle.mt-0") == "Community"
    assert "First" in text_of(pane, "div#content")
    templates = select(root, "template")
    assert [t.attrs["id"] for t in templates] == ["wp-body-1", "wp-body-2", "wp-body-3"]
    assert text_of(templates[1], "h4#smallTitle") == "Work Package 6"
    assert text_of(templates[1], "h2#mainTitle") == "Use Cases"
    assert "Second body" in text_of(templates[1], "div#content")


def test_work_field_editor_text_only_escaped_inside_template(client, wf_page):
    _block(wf_page, "work_package", 3, label=EVIL, title=EVIL, body_md="x")
    response, root = _get(client, wf_page.get_public_path())
    html = response.content.decode()
    assert "<img src=x onerror" not in html
    assert "&lt;/script&gt;&lt;img src=x onerror=alert(1)&gt;" in html
    template = select(root, "template")[3]
    assert EVIL in text_of(template, "h4#smallTitle") and EVIL in text_of(template, "h2#mainTitle")
    assert not [n for n in root.iter_descendants() if n.tag == "script" and n.text().strip()]
    tab = select(root, "#myTab > a.nav-link")[3]
    assert not any("onclick" in n.attrs for n in [tab, *tab.iter_descendants()])
    for node in root.iter_descendants():
        if node.tag == "script":
            assert "onerror" not in node.text()


def test_work_field_has_no_inline_script_and_loads_site_js(client, wf_page):
    response = site_get(client, wf_page.get_public_path())
    html = response.content.decode()
    assert "website/js/site.js" in html
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", html)


def test_work_field_contact_form_id_and_disabled(client, wf_page):
    status = SimpleNamespace(available=False, reasons=("no_key",))
    with mock.patch("website.contact.sending_status", return_value=status):
        _, root = _get(client, wf_page.get_public_path())
    assert select_one(root, "div.modular-row.form section#contact-section")
    form = select_one(root, "form#contact-form-wf2")
    assert form.attrs["name"] == "contact-form-wf2"
    assert "disabled" in select_one(form, "button[type=submit]").attrs


def test_work_field_without_packages_or_cover_renders(client):
    make_page("home", page_type="home", title="")
    wf = make_page("empty", page_type="work_field", title="Empty", menu_order=1)
    _, root = _get(client, wf.get_public_path())
    assert select(root, "template") == []
    assert select_one(root, "#tab1")
    assert select_one(root, "img.mobile-icon") is None


def test_work_field_german_labels(client):
    make_page("home", language="de", page_type="home", title="")
    wf = make_page(
        "kommunikation", language="de", page_type="work_field", title="Kommunikation", menu_order=2
    )
    _block(wf, "work_package", 0, label="AP 5", title="Titel", body_md="x")
    _, root = _get(client, wf.get_public_path())
    assert text_of(root, "section.hero-section-2 h1") == "Arbeitsfeld II Kommunikation"
    assert text_of(root, "section.section-50-50 h1.mt-0") == "Arbeitspakete"


# -- regression: hero intro and footer newsletter link ----------------------


def test_work_field_hero_shows_content_not_summary(client, wf_page):
    wf_page.content_md = "The long **hero** intro & more."
    wf_page.save()
    _, root = _get(client, wf_page.get_public_path())
    assert text_of(root, "section.hero-section-2 p.text-block") == "The long hero intro & more."


def test_work_field_hero_falls_back_to_summary(client, wf_page):
    _, root = _get(client, wf_page.get_public_path())
    assert text_of(root, "section.hero-section-2 p.text-block") == "The aim of working field II"


def test_footer_newsletter_link_only_when_page_exists(client):
    make_page("home", page_type="home", title="")
    make_page("home", language="de", page_type="home", title="")
    make_page("newsletter", page_type="article_list", title="Newsletter")
    en = site_get(client, "/en").content.decode()
    de = site_get(client, "/de").content.decode()
    assert 'data-href="/en/newsletter"' in en
    assert "/de/newsletter" not in de


def test_home_work_field_cards_use_static_icons_not_cover_image(client, home_tree):
    _, wf1, wf2 = home_tree
    wf1.cover_image = _image("cover-one")
    wf1.save()
    odd = make_page(
        "odd",
        page_type="work_field",
        title="Odd",
        parent=wf1.parent,
        menu_order=9,
        summary="s",
        cover_image=_image("cover-odd"),
    )
    response, root = _get(client, "/en")
    cards = select(root, ".feature-boxes.mt-4.h-100 > .feature-box.border")
    srcs = [[i.attrs["src"] for i in select(c, "img")] for c in cards]
    assert len(srcs[0]) == 1 and srcs[0][0].endswith("/website/images/icons/work-field-1.svg")
    assert len(srcs[1]) == 1 and srcs[1][0].endswith("/website/images/icons/work-field-2.svg")
    assert srcs[2] == []
    html = response.content.decode()
    assert wf1.cover_image.image.url not in html
    assert odd.cover_image.image.url not in html
