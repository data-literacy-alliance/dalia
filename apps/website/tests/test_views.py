import re
from unittest import mock

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import DisallowedHost
from django.http import HttpResponse, HttpResponseRedirect
from django.test import Client, RequestFactory
from pages.models import Page
from website import views
from website.tests.utils import (
    TEST_HOST,
    allow_website_hosts,
    make_page,
    parse_html,
    select,
    select_one,
    site_get,
    site_post,
    text_of,
    website_client,
)

pytestmark = pytest.mark.django_db


def _rf_get(path, **extra):
    request = RequestFactory().get(path, **extra)
    request.user = AnonymousUser()  # normally set by the authentication middleware
    return request


@pytest.fixture
def client(settings):
    return website_client(settings)


@pytest.fixture
def tree():
    home = make_page("home", page_type="home", title="")
    folder = make_page(
        "arbeitsfelder", page_type="folder", title="Working Fields", show_in_menu=True
    )
    wf = make_page(
        "qualitätssicherung",
        page_type="work_field",
        title="Quality",
        parent=folder,
        menu_order=1,
        show_in_menu=True,
    )
    legal = make_page("privacy", page_type="legal", title="Imprint", show_in_menu=False)
    Page.objects.filter(pk=legal.pk).update(content_html="<h3>Publisher</h3><p>Text</p>")
    return home, folder, wf, legal


def test_site_root_redirects_to_en(client):
    response = site_get(client, "/")
    assert response.status_code == 302
    assert response["Location"] == "/en"


def test_home_resolves_and_uses_website_layout(client, tree):
    response = site_get(client, "/en")
    assert response.status_code == 200
    doc = parse_html(response.content)
    assert text_of(doc, "title") == "Home | DALIA"
    assert select_one(doc, "html").attrs["lang"] == "en"
    assert select_one(doc, "#page-wrapper > .nav-spacer")
    assert select_one(doc, "nav#header-container .container-header")
    assert select_one(doc, "#mobileMenu.mobile-version")
    assert select_one(doc, "footer#footer-section-2")
    assert select_one(doc, "link[rel=canonical]").attrs["href"] == "https://dalia.education/en"


def test_german_home_title(client, tree):
    make_page("start", language="de", page_type="home")
    response = site_get(client, "/de")
    assert text_of(parse_html(response.content), "title") == "Startseite | DALIA"


def test_nested_unicode_slug_resolves_with_and_without_trailing_slash(client, tree):
    for path in (
        "/en/arbeitsfelder/qualit%C3%A4tssicherung",
        "/en/arbeitsfelder/qualit%C3%A4tssicherung/",
        "/en/arbeitsfelder/qualita%CC%88tssicherung",  # decomposed form of the umlaut
    ):
        response = site_get(client, path)
        assert response.status_code == 200, path
        assert "Quality" in response.content.decode()


def test_wrong_parent_chain_is_404(client, tree):
    make_page("elsewhere", page_type="folder")
    assert site_get(client, "/en/elsewhere/qualit%C3%A4tssicherung").status_code == 404
    assert site_get(client, "/en/qualit%C3%A4tssicherung").status_code == 404


def test_unknown_language_pair_and_unpublished_are_website_404(client, tree):
    home, folder, wf, legal = tree
    Page.objects.filter(pk=legal.pk).update(is_published=False)
    response = site_get(client, "/en/privacy")
    assert response.status_code == 404
    doc = parse_html(response.content)
    assert select_one(doc, "nav#header-container")  # website template, not the global 404
    assert "Page not found" in response.content.decode()
    assert site_get(client, "/de/privacy").status_code == 404
    assert site_get(client, "/en/does-not-exist").status_code == 404


def test_unpublished_ancestor_is_404(client, tree):
    home, folder, wf, legal = tree
    Page.objects.filter(pk=folder.pk).update(is_published=False)
    assert site_get(client, "/en/arbeitsfelder/qualit%C3%A4tssicherung").status_code == 404


def test_home_missing_is_404(client):
    assert site_get(client, "/en").status_code == 404


def test_too_deep_or_nul_paths_are_404(client, tree):
    assert site_get(client, "/en/a/b/c/d").status_code == 404
    assert site_get(client, "/en/a%00b").status_code == 404
    assert site_get(client, "/en/" + "x" * 300).status_code == 404


def test_blank_page_type_is_404(client):
    make_page("blank", page_type="")
    assert site_get(client, "/en/blank").status_code == 404


def test_folder_redirects_to_first_published_child(client, tree):
    home, folder, wf, legal = tree
    make_page("zzz", page_type="work_field", parent=folder, menu_order=9)
    make_page("draft", page_type="work_field", parent=folder, menu_order=0, is_published=False)
    response = site_get(client, "/en/arbeitsfelder")
    assert response.status_code == 302
    assert response["Location"] == "/en/arbeitsfelder/qualit%C3%A4tssicherung"


def test_folder_without_published_child_is_404(client):
    make_page("empty", page_type="folder")
    assert site_get(client, "/en/empty").status_code == 404


def test_legal_page_uses_legal_layout(client, tree):
    response = site_get(client, "/en/privacy")
    assert response.status_code == 200
    doc = parse_html(response.content)
    assert select_one(doc, "#header.desktop-hide-2")
    assert select_one(doc, "nav#header-container") is None
    assert text_of(doc, "h1.mt-0") == "Imprint"
    assert "Publisher" in text_of(doc, "#privacy_text h3")
    assert any(
        "css-compiled/bootstrap.min.css" in n.attrs["href"]
        for n in select(doc, "link[rel=stylesheet]")
    )


def test_alt_language_switch_with_and_without_counterpart(client, tree):
    response = site_get(client, "/en/privacy")
    doc = parse_html(response.content)
    links = {a.text().strip(): a.attrs["href"] for a in select(doc, "ul.langswitcher a")}
    assert links == {"Deutsch": "/de", "English": "/en/privacy"}
    make_page("privacy", language="de", page_type="legal", title="Impressum")
    doc = parse_html(site_get(client, "/en/privacy").content)
    links = {a.text().strip(): a.attrs["href"] for a in select(doc, "ul.langswitcher a")}
    assert links["Deutsch"] == "/de/privacy"
    assert select_one(doc, "ul.langswitcher a.active").text().strip() == "English"


def test_navigation_is_built_from_database(client, tree):
    doc = parse_html(site_get(client, "/en").content)
    items = [a.attrs["href"] for a in select(doc, "ul.me-auto > li.nav-item > a.nav-link")]
    assert items == ["/en/arbeitsfelder"]
    dropdown = [a.attrs["href"] for a in select(doc, "ul.dropdown-menu a.dropdown-item")]
    assert dropdown == ["/en/arbeitsfelder/qualit%C3%A4tssicherung"]
    footer_links = [a.attrs["href"] for a in select(doc, "#footer-section-2 a.light")]
    assert "/en/arbeitsfelder/qualit%C3%A4tssicherung" in footer_links
    assert "/en/privacy" in footer_links
    assert "/en#mission-vision" in footer_links


def test_mobile_menu_data_attributes_contain_only_integers(client, tree):
    doc = parse_html(site_get(client, "/en").content)
    show = [n.attrs["data-submenu-show"] for n in select(doc, "#mobileMenu [data-submenu-show]")]
    hide = [n.attrs["data-submenu-hide"] for n in select(doc, "#mobileMenu [data-submenu-hide]")]
    assert show == ["1"] and hide == ["1"]


INLINE_SCRIPT = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>", re.I)
INLINE_HANDLER = re.compile(r"<[a-z][^>]*\son[a-z]+\s*=", re.I)


@pytest.mark.parametrize(
    "path", ["/en", "/en/privacy", "/en/arbeitsfelder/qualit%C3%A4tssicherung"]
)
def test_pages_have_no_inline_scripts_or_event_handlers(client, tree, path):
    response = site_get(client, path)
    assert response.status_code == 200
    html = response.content.decode()
    assert not INLINE_SCRIPT.search(html)
    assert not INLINE_HANDLER.search(html)
    assert "website/js/site.js" in html


def test_no_site_prefix_leaks_into_links_or_headers(client, tree):
    for path in ("/en", "/en/privacy", "/en/arbeitsfelder/qualit%C3%A4tssicherung", "/en/nope"):
        response = site_get(client, path)
        assert "/site/" not in response.content.decode(), path
        assert "/site/" not in response.get("Location", ""), path
    assert "/site/" not in site_get(client, "/en/arbeitsfelder")["Location"]


@pytest.mark.parametrize("path", ["/en/privacy", "/en/arbeitsfelder/qualit%C3%A4tssicherung"])
def test_post_only_on_home_and_work_field(client, tree, path):
    response = site_post(client, path, {"x": "y"})
    if path.endswith("privacy"):
        assert response.status_code == 405
        assert set(response["Allow"].split(", ")) == {"GET", "HEAD"}
    else:
        assert response.status_code == 200


def test_put_is_not_allowed_on_home(client, tree):
    assert client.put("/site/en", "").status_code == 405


def test_post_to_unpublished_page_is_404(client, tree):
    home = tree[0]
    Page.objects.filter(pk=home.pk).update(is_published=False)
    assert site_post(client, "/en").status_code == 404


def test_home_and_work_field_responses_are_never_cached(client, tree):
    for path in ("/en", "/en/arbeitsfelder/qualit%C3%A4tssicherung"):
        assert "no-store" in site_get(client, path)["Cache-Control"]
        assert "no-store" in site_post(client, path, {})["Cache-Control"]
    assert "no-store" not in site_get(client, "/en/privacy").get("Cache-Control", "")


def test_contact_context_for_form_pages(client, tree):
    with mock.patch("website.views.handle_contact") as handler:
        handler.return_value = (mock.MagicMock(), None, True)
        with mock.patch("website.views.render") as render:
            render.return_value = HttpResponse("ok")
            site_get(client, "/en?sent=1")
            context = render.call_args.args[2]
    assert context["contact_enabled"] is True
    assert context["contact_sent"] is True
    assert context["contact_form_id"] == "contact-form"


def test_work_field_form_id_uses_menu_order(client, tree):
    with (
        mock.patch("website.views.handle_contact") as handler,
        mock.patch("website.views.render") as render,
    ):
        handler.return_value = (mock.MagicMock(), None, False)
        render.return_value = HttpResponse("ok")
        site_get(client, "/en/arbeitsfelder/qualit%C3%A4tssicherung")
        context = render.call_args.args[2]
    assert context["contact_form_id"] == "contact-form-wf1"
    assert context["contact_sent"] is False
    assert context["contact_enabled"] is False


def test_contact_redirect_is_returned_with_no_store(client, tree):
    with mock.patch("website.views.handle_contact") as handler:
        handler.return_value = (
            mock.MagicMock(),
            HttpResponseRedirect("/en?sent=1#contact-section"),
            True,
        )
        response = site_post(client, "/en", {})
    assert response.status_code == 302
    assert "no-store" in response["Cache-Control"]


def test_list_page_children_are_ordered_and_published_only(client):
    make_page("home", page_type="home")
    events = make_page("events", page_type="event_list", title="Events")
    make_page("old", page_type="event", parent=events, date="2024-01-01")
    make_page("new", page_type="event", parent=events, date="2025-06-01")
    make_page("undated", page_type="event", parent=events, date=None)
    make_page("draft", page_type="event", parent=events, date="2026-01-01", is_published=False)
    with mock.patch("website.views.render") as render:
        render.return_value = HttpResponse("ok")
        site_get(client, "/en/events")
        context = render.call_args.args[2]
    assert [c.slug for c in context["children"]] == ["new", "old", "undated"]
    assert context["children"][0].get_public_path() == "/en/events/new"


def test_blocks_are_grouped_by_kind(client):
    home = make_page("home", page_type="home")
    home.blocks.create(kind="link_card", title="B", sort_order=2)
    home.blocks.create(kind="link_card", title="A", sort_order=1)
    home.blocks.create(kind="hero", title="H")
    with mock.patch("website.views.render") as render:
        render.return_value = HttpResponse("ok")
        site_get(client, "/en")
        context = render.call_args.args[2]
    assert [b.title for b in context["blocks"]["link_card"]] == ["A", "B"]
    assert [b.title for b in context["blocks"]["hero"]] == ["H"]


def test_placeholder_templates_render_title_and_content(client):
    make_page("home", page_type="home")
    for page_type in ("article_list", "article", "event"):
        page = make_page(f"p-{page_type}", page_type=page_type, title=f"T {page_type}")
        Page.objects.filter(pk=page.pk).update(content_html="<p>Body text</p>")
        response = site_get(client, f"/en/p-{page_type}")
        assert response.status_code == 200
        text = response.content.decode()
        assert f"T {page_type}" in text and "Body text" in text


# -- host check -------------------------------------------------------------


@pytest.mark.parametrize(
    "host", ["search.dalia.education", "testserver", "dalia.education.evil.example", "localhost"]
)
def test_non_website_hosts_get_404(settings, tree, host):
    allow_website_hosts(settings)
    settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, "localhost"]
    client = Client(HTTP_X_FORWARDED_HOST=host)
    for path in ("/en", "/en/privacy", "/"):
        response = site_get(client, path)
        assert response.status_code == 404, (host, path)
        assert "Page not found" in response.content.decode()


def test_plain_request_without_forwarded_host_gets_404(settings, tree):
    allow_website_hosts(settings)
    assert Client().get("/site/en").status_code == 404


def test_test_host_is_served(settings, tree):
    client = website_client(settings, host=TEST_HOST)
    assert site_get(client, "/en").status_code == 200
    assert site_get(client, "/")["Location"] == "/en"


def test_www_host_is_served(settings, tree):
    client = website_client(settings, host="www.dalia.education")
    assert site_get(client, "/en").status_code == 200


def test_comma_host_list_and_disallowed_host_give_404(settings, tree):
    allow_website_hosts(settings)
    settings.ALLOWED_HOSTS = ["*"]
    request = _rf_get("/site/en", HTTP_X_FORWARDED_HOST="dalia.education, x")
    assert views.page_view(request, "en").status_code == 404
    assert (
        views.root_redirect(
            _rf_get("/site/", HTTP_X_FORWARDED_HOST="dalia.education, x")
        ).status_code
        == 404
    )
    settings.ALLOWED_HOSTS = ["dalia.education"]
    bad = _rf_get("/site/en", HTTP_X_FORWARDED_HOST="dalia.education, x")
    with pytest.raises(DisallowedHost):
        bad.get_host()
    assert views.page_view(bad, "en").status_code == 404


def test_request_not_under_site_prefix_gets_404(settings, tree):
    allow_website_hosts(settings)
    request = _rf_get("/en", HTTP_X_FORWARDED_HOST="dalia.education")
    assert views.page_view(request, "en").status_code == 404
