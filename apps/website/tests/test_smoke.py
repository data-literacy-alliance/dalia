import pytest
from django.apps import apps
from django.conf import settings
from website.tests.utils import site_get, website_client


def test_apps_installed():
    assert apps.is_installed("website")
    assert apps.is_installed("mailing")


@pytest.mark.django_db
def test_site_root_redirects_to_en(settings):
    response = site_get(website_client(settings), "/")
    assert response.status_code == 302
    assert response["Location"] == "/en"


@pytest.mark.django_db
def test_site_page_without_content_is_404(settings):
    assert site_get(website_client(settings), "/en").status_code == 404


def test_csrf_origins_include_website_hosts():
    assert "https://dalia.education" in settings.CSRF_TRUSTED_ORIGINS
    assert "https://www.dalia.education" in settings.CSRF_TRUSTED_ORIGINS
    assert "https://search.dalia.education" in settings.CSRF_TRUSTED_ORIGINS


@pytest.mark.parametrize(
    ("name", "default", "cast"),
    [
        ("WEBSITE_CONTACT_RATE_LIMIT_PER_HOUR", 5, int),
        ("WEBSITE_CONTACT_SUBNET_LIMIT_PER_HOUR", 20, int),
        ("WEBSITE_CONTACT_GLOBAL_LIMIT_PER_HOUR", 50, int),
        ("WEBSITE_CONTACT_REJECTED_LIMIT_PER_HOUR", 500, int),
        ("WEBSITE_TRUSTED_PROXY_HOPS", 1, int),
        ("MAILING_TEST_EMAIL_LIMIT_PER_HOUR", 10, int),
    ],
)
def test_website_setting_code_defaults(monkeypatch, name, default, cast):
    from config.settings.base import _env_or_default

    monkeypatch.delenv(name, raising=False)
    assert _env_or_default(name, default, cast) == default
    monkeypatch.setenv(name, "")
    assert _env_or_default(name, default, cast) == default


def test_env_or_default_uses_env_override(monkeypatch):
    from config.settings.base import _env_or_default

    monkeypatch.setenv("WEBSITE_TRUSTED_PROXY_HOPS", "3")
    assert _env_or_default("WEBSITE_TRUSTED_PROXY_HOPS", 1, int) == 3
