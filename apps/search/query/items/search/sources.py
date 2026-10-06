"""Resolution of the enabled search sources from settings.

Reads ``settings.DALIA_SEARCH_SOURCES`` and returns a validated, de-duplicated
list of known source names, failing safe to ``["fuseki"]`` so a misconfiguration
can never disable search entirely.
"""

import logging
from typing import List

from django.conf import settings

logger = logging.getLogger(__name__)

# The only source names the search coordinator knows how to run.
VALID_SEARCH_SOURCES = ("fuseki", "postgres")
_DEFAULT_SOURCES = ("fuseki",)


def get_enabled_search_sources() -> List[str]:
    """Return the ordered list of enabled, known search sources.

    Falls back to ``["fuseki"]`` (logging a warning) when the configured value
    is missing, not a list, or contains no recognised source after filtering.
    Unknown source names are dropped with a warning.
    """
    configured = getattr(settings, "DALIA_SEARCH_SOURCES", None)

    if not isinstance(configured, (list, tuple)):
        logger.warning(
            "DALIA_SEARCH_SOURCES is not a list (got %r); falling back to %s",
            configured,
            _DEFAULT_SOURCES,
        )
        return list(_DEFAULT_SOURCES)

    enabled: List[str] = []
    for raw in configured:
        name = raw.strip() if isinstance(raw, str) else raw
        if name in VALID_SEARCH_SOURCES:
            if name not in enabled:
                enabled.append(name)
        else:
            logger.warning("Ignoring unknown search source %r in DALIA_SEARCH_SOURCES", raw)

    if not enabled:
        logger.warning(
            "DALIA_SEARCH_SOURCES resolved to no known sources; falling back to %s",
            _DEFAULT_SOURCES,
        )
        return list(_DEFAULT_SOURCES)

    return enabled
