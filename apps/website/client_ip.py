"""Client IP extraction and privacy-preserving keys for rate limiting.

Only the HMAC keys returned by ``ip_key`` / ``subnet_key`` may appear in cache keys and logs.
"""

import hashlib
import hmac
import ipaddress

from django.conf import settings
from django.utils import timezone


def _parse(value: str):
    try:
        ip = ipaddress.ip_address(value.strip())
    except ValueError:
        return None
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        return ip.ipv4_mapped
    return ip


def client_ip(request) -> str:
    """Return the client address as seen by the outermost trusted proxy.

    ``X-Forwarded-For`` is split on commas and the entry at ``-WEBSITE_TRUSTED_PROXY_HOPS`` is used (never
    the first entry, which the client controls). Falls back to ``REMOTE_ADDR`` when the header is missing,
    too short or the selected entry is not a valid IP.
    """
    remote = request.META.get("REMOTE_ADDR", "")
    header = request.META.get("HTTP_X_FORWARDED_FOR", "")
    hops = max(int(settings.WEBSITE_TRUSTED_PROXY_HOPS), 1)
    if header:
        entries = [part.strip() for part in header.split(",")]
        if len(entries) >= hops:
            parsed = _parse(entries[-hops])
            if parsed is not None:
                return str(parsed)
    parsed = _parse(remote)
    return str(parsed) if parsed is not None else remote


def _hmac(value: str) -> str:
    stamp = timezone.now().strftime("%Y%m%d")
    digest = hmac.new(settings.SECRET_KEY.encode(), (value + stamp).encode(), hashlib.sha256)
    return digest.hexdigest()[:16]


def ip_key(ip: str) -> str:
    """Daily-rotating HMAC of the address."""
    return _hmac(ip)


def subnet_key(ip: str) -> str:
    """Daily-rotating HMAC of the IPv4 /24 or IPv6 /64 network containing the address."""
    parsed = _parse(ip)
    if parsed is None:
        return _hmac(ip)
    prefix = 24 if parsed.version == 4 else 64
    return _hmac(str(ipaddress.ip_network(f"{parsed}/{prefix}", strict=False)))
