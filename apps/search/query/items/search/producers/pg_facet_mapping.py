"""Mapping layer from curation vocabulary instances to canonical Fuseki facet value strings.

For each FacetObject, this module provides:
- ``FACET_VOCAB_MAP``: registry linking each facet to its vocab model and a per-instance resolver.
- ``resolve_facet_value``: maps one vocab instance to the canonical value string used in search
  responses (i.e. ``str(node)`` for each key in ``FacetObject.items``), or ``None`` when the
  instance cannot be mapped (blank uri, no match, missing field).
- ``build_reverse_facet_map``: builds a ``{value_string: set_of_pks}`` dict over all active rows
  of the facet's vocab model, suitable for translating incoming ``selectedFacets`` values into
  ORM ``__in`` PK filters.

This module is read-only: it never writes to the database.
It is used by the postgres producer and wired into the search coordinator via comprehensive_search.py.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Set, Tuple, Type

from django.db import models

from curation.models.communities import Community
from curation.models.vocabularies import (
    Discipline,
    FileFormat,
    Language,
    LearningResourceType,
    License,
    MediaType,
    ProficiencyLevel,
    TargetGroup,
)
from search.query.items.facets.facet_objects import (
    COMMUNITY_FACET,
    DISCIPLINE_FACET,
    FILE_FORMAT_FACET,
    LANGUAGE_FACET,
    LEARNING_RESOURCE_TYPE_FACET,
    LICENSE_FACET,
    MEDIA_TYPE_FACET,
    PROFICIENCY_LEVEL_FACET,
    TARGET_AUDIENCE_FACET,
    FacetObject,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical value sets
# ---------------------------------------------------------------------------
# Computed once at import time from the FacetObject.items dicts.  The search
# response emits each facet item's value as ``str(node)`` (see
# ``_compile_facets_with_counts`` in comprehensive_search.py), so the
# canonical set for facet F is ``{str(node) for node in F.items}``.


def _canonical_values(facet: FacetObject) -> Dict[str, str]:
    """Return ``{str(node): str(node)}`` for all nodes in *facet*.items.

    We keep a plain dict (value_string -> value_string) so callers can do
    O(1) membership tests and retrieve the exact canonical casing in one step.
    """
    return {str(node): str(node) for node in facet.items}


# ---------------------------------------------------------------------------
# ISO 639-1 → ISO 639-3 lookup (only the four languages present in the facet)
# ---------------------------------------------------------------------------
_ISO1_TO_ISO3: Dict[str, str] = {
    "en": "eng",
    "fr": "fra",
    "de": "deu",
    "es": "spa",
}
_LEXVO_BASE = "http://lexvo.org/id/iso639-3/"

# ProprietaryLicense is a key in LICENSE_FACET.items, so step 1 (uri match) handles it.

# ---------------------------------------------------------------------------
# Per-facet resolver callables
# ---------------------------------------------------------------------------


def _resolve_by_uri(canonical: Dict[str, str], instance) -> Optional[str]:
    """Default resolver: strip and look up ``instance.uri`` in *canonical*."""
    try:
        uri = (instance.uri or "").strip()
    except AttributeError:
        return None
    if not uri:
        return None
    return canonical.get(uri)


def _make_uri_resolver(facet: FacetObject) -> Callable[[object], Optional[str]]:
    canonical = _canonical_values(facet)

    def _resolve(instance) -> Optional[str]:
        return _resolve_by_uri(canonical, instance)

    return _resolve


def _make_community_resolver() -> Callable[[object], Optional[str]]:
    """Community resolver: returns instance.uri directly, or a UUID-based URI as fallback.

    Unlike the generic URI resolver, this does NOT filter against the hardcoded
    COMMUNITY_FACET.items dict — it maps ANY community with a URI so that
    build_reverse_facet_map covers all PG communities, not just the 37 known ones.
    """

    def _resolve(instance) -> Optional[str]:
        try:
            uri = (instance.uri or "").strip()
            if uri:
                return uri
            uuid_val = getattr(instance, "uuid", None)
            if uuid_val:
                return f"https://id.dalia.education/community/{uuid_val}"
        except AttributeError:
            pass
        return None

    return _resolve


def _make_license_resolver(facet: FacetObject) -> Callable[[object], Optional[str]]:
    canonical = _canonical_values(facet)

    def _resolve(instance) -> Optional[str]:
        # 1. Try instance.uri directly.
        try:
            uri = (instance.uri or "").strip()
        except AttributeError:
            uri = ""
        if uri and uri in canonical:
            return canonical[uri]

        # 2. Try derived SPDX URL from spdx_id.
        try:
            spdx_id = (instance.spdx_id or "").strip()
        except AttributeError:
            spdx_id = ""
        if spdx_id:
            derived = f"http://spdx.org/licenses/{spdx_id}"
            if derived in canonical:
                return canonical[derived]

        return None

    return _resolve


def _make_file_format_resolver(facet: FacetObject) -> Callable[[object], Optional[str]]:
    # Build a case-insensitive lookup: upper(canonical_string) -> canonical_string
    upper_to_canonical: Dict[str, str] = {}
    for node in facet.items:
        val = str(node)
        upper_to_canonical[val.upper()] = val

    def _resolve(instance) -> Optional[str]:
        try:
            label = (instance.label or "").strip().lstrip(".").upper()
        except AttributeError:
            label = ""
        if label:
            hit = upper_to_canonical.get(label)
            if hit is not None:
                return hit
        # Slug fallback: slug is the slugified label (strips leading dots, lowercases).
        try:
            slug = (instance.slug or "").strip().upper()
        except AttributeError:
            slug = ""
        if slug and slug != label:
            return upper_to_canonical.get(slug)
        return None

    return _resolve


def _make_language_resolver(facet: FacetObject) -> Callable[[object], Optional[str]]:
    canonical = _canonical_values(facet)

    def _resolve(instance) -> Optional[str]:
        # 1. Try instance.uri directly.
        try:
            uri = (instance.uri or "").strip()
        except AttributeError:
            uri = ""
        if uri and uri in canonical:
            return canonical[uri]

        # 2. Map ISO 639-1 code to lexvo ISO 639-3 URI.
        try:
            code = (instance.code or "").strip().lower()
        except AttributeError:
            code = ""
        if code:
            iso3 = _ISO1_TO_ISO3.get(code)
            if iso3:
                derived = f"{_LEXVO_BASE}{iso3}"
                if derived in canonical:
                    return canonical[derived]

        return None

    return _resolve


# ---------------------------------------------------------------------------
# Registry dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FacetVocabMapping:
    """Associates a FacetObject with its curation vocab model and resolver."""

    model: Type[models.Model]
    resolver: Callable[[object], Optional[str]]

    # Fields passed to .only() when querying the vocab model.  Defaults to
    # ("pk", "uri") which covers all URI-based resolvers.
    only_fields: Tuple[str, ...] = ("pk", "uri")

    # Informational only — the M2M relation name on ResourceContent belongs to
    # S6. Included here as documentation so S6 can read it from this registry.
    m2m_relation: Optional[str] = None


# ---------------------------------------------------------------------------
# Public registry
# ---------------------------------------------------------------------------

FACET_VOCAB_MAP: Dict[FacetObject, FacetVocabMapping] = {
    TARGET_AUDIENCE_FACET: FacetVocabMapping(
        model=TargetGroup,
        resolver=_make_uri_resolver(TARGET_AUDIENCE_FACET),
        m2m_relation="target_groups",
    ),
    MEDIA_TYPE_FACET: FacetVocabMapping(
        model=MediaType,
        resolver=_make_uri_resolver(MEDIA_TYPE_FACET),
        m2m_relation="media_types",
    ),
    LEARNING_RESOURCE_TYPE_FACET: FacetVocabMapping(
        model=LearningResourceType,
        resolver=_make_uri_resolver(LEARNING_RESOURCE_TYPE_FACET),
        m2m_relation="learning_resource_types",
    ),
    LANGUAGE_FACET: FacetVocabMapping(
        model=Language,
        resolver=_make_language_resolver(LANGUAGE_FACET),
        only_fields=("pk", "uri", "code"),
        m2m_relation="languages",
    ),
    PROFICIENCY_LEVEL_FACET: FacetVocabMapping(
        model=ProficiencyLevel,
        resolver=_make_uri_resolver(PROFICIENCY_LEVEL_FACET),
        m2m_relation="proficiency_levels",
    ),
    DISCIPLINE_FACET: FacetVocabMapping(
        model=Discipline,
        resolver=_make_uri_resolver(DISCIPLINE_FACET),
        m2m_relation="disciplines",
    ),
    LICENSE_FACET: FacetVocabMapping(
        model=License,
        resolver=_make_license_resolver(LICENSE_FACET),
        only_fields=("pk", "uri", "spdx_id"),
        m2m_relation="licenses",
    ),
    FILE_FORMAT_FACET: FacetVocabMapping(
        model=FileFormat,
        resolver=_make_file_format_resolver(FILE_FORMAT_FACET),
        only_fields=("pk", "uri", "label", "slug"),
        m2m_relation="file_formats",
    ),
    COMMUNITY_FACET: FacetVocabMapping(
        model=Community,
        resolver=_make_community_resolver(),
        # Returns uri-or-uuid-uri for ANY active community (not just the 37 hardcoded ones).
        # community_relations__community join is handled specially in postgres_producer.
        only_fields=("pk", "uri", "uuid"),
        m2m_relation=None,
    ),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_facet_value(facet: FacetObject, instance) -> Optional[str]:
    """Return the canonical facet value string for *instance*, or ``None``.

    ``None`` means the instance cannot be mapped to any value in the facet
    (blank uri, unrecognised code, no match).  Callers should skip ``None``
    rows — this is expected and normal, not an error.  This function never
    raises.
    """
    mapping = FACET_VOCAB_MAP.get(facet)
    if mapping is None:
        logger.debug("resolve_facet_value: facet %r not in FACET_VOCAB_MAP", facet.label)
        return None
    try:
        return mapping.resolver(instance)
    except Exception:
        logger.debug(
            "resolve_facet_value: unexpected error for facet %r instance pk=%r",
            facet.label,
            getattr(instance, "pk", "?"),
            exc_info=True,
        )
        return None


def build_reverse_facet_map(facet: FacetObject) -> Dict[str, Set[int]]:
    """Return ``{value_string: set_of_pks}`` for all active rows of *facet*'s vocab model.

    Rows whose ``resolve_facet_value`` returns ``None`` are silently skipped.
    This map is used by the PG search producer (S6) to translate incoming
    ``selectedFacets`` value strings into ORM ``__in`` PK filters.

    This is a read-only query.  It is not cached here — callers that need
    caching should wrap this function.
    """
    mapping = FACET_VOCAB_MAP.get(facet)
    if mapping is None:
        logger.debug("build_reverse_facet_map: facet %r not in FACET_VOCAB_MAP", facet.label)
        return {}

    result: Dict[str, Set[int]] = {}
    qs = mapping.model.objects.filter(is_active=True).only(*mapping.only_fields)

    for instance in qs.iterator():
        value = resolve_facet_value(facet, instance)
        if value is None:
            continue
        if value not in result:
            result[value] = set()
        result[value].add(instance.pk)

    logger.info(
        "build_reverse_facet_map: facet=%r model=%s distinct_values=%d",
        facet.label,
        mapping.model.__name__,
        len(result),
    )
    return result
