"""Website host detection (same patterns as the nginx ``dalia_site`` map)."""

import re

_WEBSITE_HOST_PATTERNS = (
    re.compile(r"(www\.)?dalia\.education"),
    re.compile(r"dalia-home-[a-z0-9-]+\.web\.gateway\.ionos\.coscine\.dev"),
)


def is_website_host(host: str) -> bool:
    """True when ``host`` is exactly a public website host name.

    Same as the nginx map: a value with a port or a comma (a forwarded-host
    list) is never a website host.
    """
    if not host or "," in host:
        return False
    bare = host.lower()
    return any(pattern.fullmatch(bare) for pattern in _WEBSITE_HOST_PATTERNS)
