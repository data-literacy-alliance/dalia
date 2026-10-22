import pytest
from pages.models import Page
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def _get(slug, lang):
    return APIClient().get(f"/api/v1/pages/{slug}/{lang}/")


def test_search_page_returned():
    Page.objects.create(slug="privacy-policy", language="en", content_md="search body")
    r = _get("privacy-policy", "en")
    assert r.status_code == 200
    assert r.json()["content_md"] == "search body"
    assert set(r.json()) == {"slug", "language", "content_md", "updated_at"}


def test_website_only_slug_is_404(monkeypatch):
    _stub_render(monkeypatch)
    Page.objects.create(
        site="website", slug="only-site", language="en", page_type="legal", title="T", content_md=""
    )
    assert _get("only-site", "en").status_code == 404


def test_search_page_wins_when_slug_shared(monkeypatch):
    _stub_render(monkeypatch)
    Page.objects.create(
        site="website",
        slug="privacy-policy",
        language="en",
        page_type="legal",
        title="W",
        content_md="website body",
    )
    Page.objects.create(slug="privacy-policy", language="en", content_md="search body")
    assert _get("privacy-policy", "en").json()["content_md"] == "search body"


def _stub_render(monkeypatch):
    import sys
    import types

    mod = types.ModuleType("pages.rendering")
    mod.render_markdown = lambda md: f"<p>{md}</p>"
    monkeypatch.setitem(sys.modules, "pages.rendering", mod)
