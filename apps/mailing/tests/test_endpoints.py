import secrets
import socket
from unittest import mock

import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings
from mailing import connection_types as ct
from mailing import crypto
from mailing.exceptions import UnsafeEndpointError
from mailing.models import EmailProvider

GAI = "mailing.connection_types.socket.getaddrinfo"


def addrs(*ips):
    return [
        (socket.AF_INET6 if ":" in ip else socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))
        for ip in ips
    ]


@pytest.fixture(autouse=True)
def _key(tmp_path):
    path = tmp_path / "key"
    path.write_text(secrets.token_hex(32))
    crypto._reset_cache()
    with override_settings(EMAIL_FERNET_KEY_FILE=str(path)):
        yield
    crypto._reset_cache()


def smtp(**kw):
    data = {
        "name": "p",
        "connection_type": "smtp",
        "host": "mail.example.org",
        "port": 587,
        "from_email": "a@example.org",
    }
    data.update(kw)
    return EmailProvider(**data)


def api(ctype="sendgrid", **kw):
    data = {"name": "p", "connection_type": ctype, "from_email": "a@example.org"}
    data.update(kw)
    return EmailProvider(**data)


PUBLIC = addrs("93.184.216.34")


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",
        "192.168.1.10",
        "10.88.1.1",
        "192.168.1.1",
        "169.254.1.1",
        "100.64.0.1",
        "::1",
        "fe80::1",
        "0.0.0.0",
        "224.0.0.1",
        "::ffff:127.0.0.1",
        "172.16.0.1",
    ],
)
def test_blocked_addresses_rejected(ip):
    with mock.patch(GAI, return_value=addrs(ip)):
        with pytest.raises(ValidationError) as info:
            ct.validate_endpoint(smtp())
        assert "host" in info.value.message_dict
        with pytest.raises(UnsafeEndpointError):
            ct.check_endpoint_at_connect(smtp())


def test_mixed_public_and_private_rejected():
    with mock.patch(GAI, return_value=addrs("93.184.216.34", "10.0.0.1")):
        with pytest.raises(ValidationError):
            ct.validate_endpoint(smtp())


@pytest.mark.parametrize("ip", ["93.184.216.34", "2606:2800:220:1:248:1893:25c8:1946"])
def test_public_accepted(ip):
    with mock.patch(GAI, return_value=addrs(ip)):
        ct.validate_endpoint(smtp())
        ct.check_endpoint_at_connect(smtp())


def test_resolution_failure():
    with mock.patch(GAI, side_effect=socket.gaierror):
        with pytest.raises(ValidationError):
            ct.validate_endpoint(smtp())
        with pytest.raises(UnsafeEndpointError):
            ct.check_endpoint_at_connect(smtp())


def test_clean_runs_endpoint_validation():
    with mock.patch(GAI, return_value=addrs("127.0.0.1")):
        with pytest.raises(ValidationError):
            smtp().clean()


@pytest.mark.parametrize(
    "url",
    [
        "http://api.sendgrid.com/v3",
        "https://user@api.sendgrid.com/v3",
        "https://user:pw@api.sendgrid.com/v3",
        "https://api.sendgrid.com/v3?x=1",
        "https://api.sendgrid.com/v3#f",
        "https://evil.example.org/v3",
        "https://api.sendgrid.com.evil.example.org/",
    ],
)
def test_bad_api_url_rejected(url):
    with pytest.raises(ValidationError) as info:
        ct.validate_endpoint(api(api_url=url))
    assert "api_url" in info.value.message_dict


def test_allowlisted_api_url_accepted_without_dns():
    with mock.patch(GAI, side_effect=AssertionError("no DNS expected")):
        ct.validate_endpoint(api(api_url="https://api.sendgrid.com/v3/mail/send"))
        ct.validate_endpoint(api("mailgun", api_url="https://API.EU.mailgun.net/v3"))
        ct.validate_endpoint(api())


def test_custom_endpoint_foreign_host_public_https_accepted():
    provider = api(api_url="https://relay.example.org/v3", custom_endpoint=True)
    with mock.patch(GAI, return_value=PUBLIC):
        ct.validate_endpoint(provider)
        ct.check_endpoint_at_connect(provider)


def test_custom_endpoint_private_host_rejected():
    provider = api(api_url="https://relay.example.org/v3", custom_endpoint=True)
    with mock.patch(GAI, return_value=addrs("10.0.0.5")):
        with pytest.raises(ValidationError):
            ct.validate_endpoint(provider)
        with pytest.raises(UnsafeEndpointError):
            ct.check_endpoint_at_connect(provider)


@pytest.mark.parametrize(
    "url",
    ["http://relay.example.org/", "https://u@relay.example.org/", "https://relay.example.org/?a=1"],
)
def test_custom_endpoint_does_not_lift_url_rules(url):
    with mock.patch(GAI, return_value=PUBLIC):
        with pytest.raises(ValidationError):
            ct.validate_endpoint(api(api_url=url, custom_endpoint=True))


def test_postal_requires_custom_endpoint():
    provider = api("postal", api_url="https://postal.example.org")
    with pytest.raises(ValidationError) as info:
        ct.validate_endpoint(provider)
    assert "custom_endpoint" in info.value.message_dict
    provider.custom_endpoint = True
    with mock.patch(GAI, return_value=PUBLIC):
        ct.validate_endpoint(provider)


def test_security_none_with_credentials_rejected():
    with mock.patch(GAI, return_value=PUBLIC):
        with pytest.raises(ValidationError) as info:
            ct.validate_endpoint(smtp(security="none", username="u"))
        assert "security" in info.value.message_dict
        provider = smtp(security="none")
        provider.set_secret("password", "pw")
        with pytest.raises(ValidationError):
            ct.validate_endpoint(provider)
        ct.validate_endpoint(smtp(security="none"))


@pytest.mark.parametrize("port", [25, 465, 587, 2525])
def test_allowed_ports(port):
    with mock.patch(GAI, return_value=PUBLIC):
        ct.validate_endpoint(smtp(port=port))


def test_port_2526_requires_custom_endpoint():
    with mock.patch(GAI, return_value=PUBLIC):
        with pytest.raises(ValidationError) as info:
            ct.validate_endpoint(smtp(port=2526))
        assert "port" in info.value.message_dict
        ct.validate_endpoint(smtp(port=2526, custom_endpoint=True))
        with pytest.raises(ValidationError):
            ct.validate_endpoint(smtp(port=70000, custom_endpoint=True))


def test_inapplicable_fields_must_be_empty():
    with pytest.raises(ValidationError) as info:
        ct.validate_endpoint(api(host="mail.example.org"))
    assert "host" in info.value.message_dict
    with mock.patch(GAI, return_value=PUBLIC):
        with pytest.raises(ValidationError) as info:
            ct.validate_endpoint(smtp(api_url="https://api.sendgrid.com"))
        assert "api_url" in info.value.message_dict


def test_smtp_requires_host_and_port():
    with pytest.raises(ValidationError) as info:
        ct.validate_endpoint(smtp(host="", port=None))
    assert {"host", "port"} <= set(info.value.message_dict)
