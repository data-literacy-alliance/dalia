import pytest
from website.hosts import is_website_host


@pytest.mark.parametrize(
    "host",
    [
        "dalia.education",
        "www.dalia.education",
        "DALIA.Education",
        "dalia-home-test.web.gateway.ionos.coscine.dev",
    ],
)
def test_website_hosts(host):
    assert is_website_host(host)


@pytest.mark.parametrize(
    "host",
    [
        "",
        "search.dalia.education",
        "testserver",
        "localhost:7087",
        "dalia.education.evil.example",
        "evil-dalia.education",
        "sub.dalia.education",
        "www.www.dalia.education",
        "dalia.education, x",
        "dalia.education,search.dalia.education",
        "dalia-home-.web.gateway.ionos.coscine.dev.evil.example",
        "dalia-home-test.web.gateway.ionos.coscine.dev.evil.example",
        "dalia.education:abc",
        "dalia.education:443",
        "www.dalia.education:80",
        "dalia-home-zubilewicz.web.gateway.ionos.coscine.dev:8443",
        "dalia.education\n",
    ],
)
def test_other_hosts(host):
    assert not is_website_host(host)


def test_hosts_agree_with_nginx_map():
    """Parity with docker/nginx.conf ``dalia_site``: patterns are anchored, no port allowed."""
    from pathlib import Path

    conf = Path(__file__).resolve().parents[3] / "docker" / "nginx.conf"
    if not conf.exists():
        pytest.skip("nginx.conf not mounted")
    text = conf.read_text()
    assert r"~*^(www\.)?dalia\.education$" in text
    assert r"~*^dalia-home-[a-z0-9-]+\.web\.gateway\.ionos\.coscine\.dev$" in text
