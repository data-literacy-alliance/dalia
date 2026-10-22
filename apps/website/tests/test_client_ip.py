from datetime import timedelta
from unittest import mock

import pytest
from django.test import RequestFactory
from django.utils import timezone
from website import client_ip as cip

rf = RequestFactory()


def _req(xff=None, remote="10.0.0.1"):
    extra = {"REMOTE_ADDR": remote}
    if xff is not None:
        extra["HTTP_X_FORWARDED_FOR"] = xff
    return rf.get("/", **extra)


@pytest.mark.parametrize(
    ("hops", "xff", "expected"),
    [
        (1, "6.6.6.6, 5.5.5.5, 1.2.3.4", "1.2.3.4"),
        (1, "1.2.3.4", "1.2.3.4"),
        (2, "6.6.6.6, 1.2.3.4, 9.9.9.9", "1.2.3.4"),
        (3, "6.6.6.6, 1.2.3.4, 8.8.8.8, 9.9.9.9", "1.2.3.4"),
    ],
)
def test_client_ip_uses_entry_at_trusted_hops(settings, hops, xff, expected):
    settings.WEBSITE_TRUSTED_PROXY_HOPS = hops
    assert cip.client_ip(_req(xff)) == expected


def test_client_ip_hops_two_picks_second_from_end(settings):
    settings.WEBSITE_TRUSTED_PROXY_HOPS = 2
    assert cip.client_ip(_req("6.6.6.6, 5.5.5.5, 1.2.3.4, 10.0.0.9")) == "1.2.3.4"


def test_client_ip_hops_three_picks_third_from_end(settings):
    settings.WEBSITE_TRUSTED_PROXY_HOPS = 3
    assert cip.client_ip(_req("6.6.6.6, 5.5.5.5, 1.2.3.4, 10.0.0.9, 10.0.0.8")) == "1.2.3.4"


def test_client_ip_never_first_entry(settings):
    settings.WEBSITE_TRUSTED_PROXY_HOPS = 1
    assert cip.client_ip(_req("6.6.6.6, 1.2.3.4")) == "1.2.3.4"


def test_malformed_entry_falls_back_to_remote_addr(settings):
    settings.WEBSITE_TRUSTED_PROXY_HOPS = 1
    assert cip.client_ip(_req("1.2.3.4, not-an-ip", remote="10.0.0.1")) == "10.0.0.1"


def test_too_short_header_falls_back_to_remote_addr(settings):
    settings.WEBSITE_TRUSTED_PROXY_HOPS = 2
    assert cip.client_ip(_req("1.2.3.4", remote="10.0.0.1")) == "10.0.0.1"


def test_missing_header_falls_back_to_remote_addr():
    assert cip.client_ip(_req(None, remote="10.0.0.1")) == "10.0.0.1"


def test_ipv6_entry_is_normalised(settings):
    settings.WEBSITE_TRUSTED_PROXY_HOPS = 1
    assert cip.client_ip(_req("2001:DB8:0:0:0:0:0:1")) == "2001:db8::1"


def test_ipv4_mapped_ipv6_is_mapped_to_ipv4(settings):
    settings.WEBSITE_TRUSTED_PROXY_HOPS = 1
    assert cip.client_ip(_req("::ffff:1.2.3.4")) == "1.2.3.4"


def test_ip_key_is_short_hex_and_hides_address():
    key = cip.ip_key("1.2.3.4")
    assert len(key) == 16
    int(key, 16)
    assert "1.2.3.4" not in key


def test_subnet_key_groups_ipv4_slash_24():
    assert cip.subnet_key("1.2.3.4") == cip.subnet_key("1.2.3.200")
    assert cip.subnet_key("1.2.3.4") != cip.subnet_key("1.2.4.4")


def test_subnet_key_groups_ipv6_slash_64():
    assert cip.subnet_key("2001:db8:0:1::1") == cip.subnet_key("2001:db8:0:1:ffff::2")
    assert cip.subnet_key("2001:db8:0:1::1") != cip.subnet_key("2001:db8:0:2::1")


def test_subnet_key_differs_from_ip_key():
    assert cip.subnet_key("1.2.3.4") != cip.ip_key("1.2.3.4")


def test_keys_rotate_with_the_date():
    today = timezone.now()
    tomorrow = today + timedelta(days=1)
    with mock.patch("website.client_ip.timezone.now", return_value=today):
        a_ip, a_net = cip.ip_key("1.2.3.4"), cip.subnet_key("1.2.3.4")
    with mock.patch("website.client_ip.timezone.now", return_value=tomorrow):
        b_ip, b_net = cip.ip_key("1.2.3.4"), cip.subnet_key("1.2.3.4")
    assert a_ip != b_ip
    assert a_net != b_net


def test_keys_depend_on_secret_key(settings):
    first = cip.ip_key("1.2.3.4")
    settings.SECRET_KEY = "another-secret-key-" + "x" * 40
    assert cip.ip_key("1.2.3.4") != first
