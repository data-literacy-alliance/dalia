"""PostgreSQL search producer — queries live ResourceContent rows.

Translates an :class:`~search.api_models.api_models.ItemSearchRequest` into an
ORM queryset over :class:`~curation.models.ResourceContent`, applies date and
facet filters, maps each result row to a
:class:`~search.api_models.api_models.Resource` dataclass, and builds the 9
standard facets in the same shape that the Fuseki producer returns via
:func:`~search.query.items.search.comprehensive_search._compile_facets_with_counts`.

Constraints
-----------
* Read-only ORM — no writes, no raw SQL.
* Never raises on missing or malformed optional data; rows that fail to map are
  skipped and logged at WARNING level.
* ``source="postgres"`` is set in the Resource mapping (see ``_map_content``).
* This producer is registered in ``_SEARCH_PRODUCERS`` and ``_CANDIDATE_PRODUCERS``
  in ``comprehensive_search.py``.
"""

from __future__ import annotations

import datetime
import logging
from collections import Counter
from typing import Dict, List, Optional, Set

from rdflib import URIRef

from django.db.models import Count, F
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.utils.text import slugify

from curation.models import ResourceContent
from curation.models.communities import Community as CommunityORM
from search.api_models.api_models import (
    Community,
    Facet,
    FacetCategory,
    FacetItem,
    ItemSearchRequest,
    ItemSearchResult,
    LabelValueItem,
    License,
    OrganizationAuthor,
    PersonAuthor,
    RelatedWork,
    Resource,
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
from search.query.items.search.producers.pg_facet_mapping import (
    FACET_VOCAB_MAP,
    build_reverse_facet_map,
    resolve_facet_value,
)
from search.query.items.search.text_search import (
    _ITEM_SEARCH_FACETS,
    _ITEM_SEARCH_FACETS_MAPPED_BY_KEY,
)

logger = logging.getLogger(__name__)

__all__ = ["postgres_search", "postgres_candidates", "postgres_facets", "postgres_hydrate"]

# Map facet → the attribute names used for the ResourceSpecial list field.
_FACET_TO_SPECIAL_ATTR: Dict[FacetObject, str] = {
    TARGET_AUDIENCE_FACET: "target_groups",
    MEDIA_TYPE_FACET: "media_types",
    LEARNING_RESOURCE_TYPE_FACET: "learning_resource_types",
    LANGUAGE_FACET: "languages",
    PROFICIENCY_LEVEL_FACET: "proficiency_levels",
    DISCIPLINE_FACET: "disciplines",
}

# FTS configuration — must match the GIN index expression in the model Meta.
_FTS_CONFIG = "english"
_BROWSE_ALL = {"", "*", "**"}


# ---------------------------------------------------------------------------
# Text-query hook
# ---------------------------------------------------------------------------


def _apply_text_query(qs, query: Optional[str]):  # noqa: ANN001
    """Apply Postgres full-text search or pass through as browse-all.

    Returns a (queryset, fts_active) tuple.  When ``fts_active`` is True the
    queryset carries ``_rank`` annotation and should be ordered by ``-_rank``.
    When False the caller should order by ``-created``.

    Filters on the STORED ``search_vector`` generated column so the planner
    can use the plain GIN index without a config bind-param.  Keywords are
    intentionally excluded; extending the vector to include them would require
    a model/migration change (future work).
    """
    q = (query or "").strip()
    if q in {"", "*", "**"}:
        return qs, False

    search_query = SearchQuery(q, config=_FTS_CONFIG)
    qs = qs.annotate(_rank=SearchRank(F("search_vector"), search_query)).filter(
        search_vector=search_query
    )
    return qs, True


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def postgres_search(request: ItemSearchRequest) -> ItemSearchResult:
    """Query live ResourceContent and return a paged, faceted search result.

    Parameters
    ----------
    request:
        An :class:`~search.api_models.api_models.ItemSearchRequest` describing
        the query, pagination, date filters, and selected facets.

    Returns
    -------
    ItemSearchResult
        ``count`` is the total matching rows (after filters, before pagination).
        ``results`` contains only the page rows mapped to
        :class:`~search.api_models.api_models.Resource` dataclasses.
        ``facets`` is the list of 9 standard facets with counts over the full
        filtered set (not just the page).

    Performance notes
    -----------------
    * ``_base_queryset()`` fetches only the relations needed for facet counting
      (8 vocab M2Ms + community_relations__community).
    * The heavy author/keyword/link relations are prefetched only on the page
      slice after pagination, avoiding materialising the full result set with
      the heavy graph.
    * Facet counting still iterates the filtered rows in Python.  At current
      scale this is acceptable; a future optimisation could push counts to DB
      aggregation, but that would change count semantics and is out of scope.
    """
    # Light base queryset — enough for facet counting.
    filtered = _base_queryset()

    # Apply date filters (fail-open on invalid dates).
    filtered = _apply_date_filters(filtered, request)

    # Apply selected-facet filters.
    facet_filters_applied = bool(request.selectedFacets)
    filtered = _apply_facet_filters(filtered, request)

    # Text-query: FTS or browse-all.
    filtered, fts_active = _apply_text_query(filtered, request.query)

    # distinct() is applied by _apply_facet_filters when M2M joins are added.
    # After FTS annotation we do not need an extra distinct.

    # Total count via DB — no materialisation.
    total = filtered.count()

    # Determine active value strings per facet (for ``active`` flag).
    active_values_by_facet = _extract_active_value_strings(request)

    # Build facets over the FULL filtered set (same as Fuseki behaviour).
    # The light queryset (vocab M2Ms + community_relations) is sufficient here.
    facets = _build_facets(filtered, active_values_by_facet)

    # Paginate: order, slice, then add the HEAVY prefetch only on the page.
    offset = request.offset
    limit = request.limit

    order_fields = ["-_rank", "-created"] if fts_active else ["-created"]
    page_qs = filtered.order_by(*order_fields)[offset : offset + limit]

    # Hydrate the heavy relations only on the page rows.
    page_qs = page_qs.prefetch_related(
        "people",
        "organizations",
        "keywords",
        "links",
        "related_items__relation_type",
    )
    page = list(page_qs)
    results = _map_page(page)

    result = ItemSearchResult()
    result.count = total
    result.offset = offset
    result.limit = limit
    result.results = results
    result.facets = facets
    return result


# ---------------------------------------------------------------------------
# Queryset helpers
# ---------------------------------------------------------------------------


def _base_queryset():
    """Return the live queryset with light prefetch graph for facet counting.

    Only prefetches the 8 vocab M2Ms and community_relations__community — the
    minimum needed to build facet counts.  The heavy author/keyword/link
    relations are added later, only on the page slice.
    """
    return (
        ResourceContent.objects.filter(
            is_active=True,
            resource__is_published=True,
            resource__is_removed=False,
        )
        .select_related("resource")
        .prefetch_related(
            "learning_resource_types",
            "disciplines",
            "licenses",
            "proficiency_levels",
            "target_groups",
            "file_formats",
            "media_types",
            "languages",
            "community_relations__community",
        )
    )


def _apply_date_filters(qs, request: ItemSearchRequest):
    """Apply publication_date range filters, ignoring blank/invalid values."""
    after_raw = (request.datePublished_after or "").strip()
    before_raw = (request.datePublished_before or "").strip()

    if after_raw:
        try:
            after_date = datetime.date.fromisoformat(after_raw)
            qs = qs.filter(publication_date__gte=after_date)
        except ValueError:
            logger.debug("postgres_search: ignoring invalid datePublished_after=%r", after_raw)

    if before_raw:
        try:
            before_date = datetime.date.fromisoformat(before_raw)
            qs = qs.filter(publication_date__lte=before_date)
        except ValueError:
            logger.debug("postgres_search: ignoring invalid datePublished_before=%r", before_raw)

    return qs


def _apply_facet_filters(qs, request: ItemSearchRequest):
    """Translate selectedFacets into M2M filters with configurable AND/OR logic.

    Within each facet group: operator comes from SelectedFacet.operator ('OR' default).
    Between facet groups: operator comes from ItemSearchRequest.crossFacetOperators[i] ('AND' default).

    OR within-group: union all vocab PKs for selected values, apply one __in filter.
    AND within-group: chain separate .filter() calls (resource must match all values).
    Cross-group AND (default): intersect per-group PK sets.
    Cross-group OR: union per-group PK sets.

    Returns qs filtered by pk__in — no M2M join duplication, no .distinct() needed.
    """
    if not request.selectedFacets:
        return qs

    selected_list = [sf for sf in request.selectedFacets if sf.selected]
    if not selected_list:
        return qs

    cross_ops = list(getattr(request, "crossFacetOperators", None) or [])
    _reverse_map_cache: Dict[FacetObject, Dict[str, Set[int]]] = {}

    def _apply_single_value(base, facet, mapping, pks):
        """Apply one set of vocab PKs to the queryset for this facet."""
        if facet is COMMUNITY_FACET:
            return base.filter(community_relations__community__in=pks)
        if mapping is None or mapping.m2m_relation is None:
            logger.warning("postgres_search: no m2m_relation for facet %r; skipping", facet.label)
            return base
        return base.filter(**{f"{mapping.m2m_relation}__in": pks})

    def _group_pks(selected) -> Set[int]:
        """Compute the set of ResourceContent PKs matching one SelectedFacet group."""
        facet = _ITEM_SEARCH_FACETS_MAPPED_BY_KEY.get(URIRef(selected.key))
        if facet is None:
            logger.debug("postgres_search: unknown facet key %r; skipping", selected.key)
            return None  # None = skip this group entirely

        if facet not in _reverse_map_cache:
            _reverse_map_cache[facet] = build_reverse_facet_map(facet)
        reverse_map = _reverse_map_cache[facet]

        mapping = FACET_VOCAB_MAP.get(facet)
        within_op = (getattr(selected, "operator", None) or "OR").upper()

        # For DISCIPLINE_FACET: expand each selected URI to all its descendants
        # so that selecting a parent discipline includes all sub-disciplines.
        effective_selected = list(selected.selected)
        if facet is DISCIPLINE_FACET:
            desc_map = _get_disc_descendants_map()
            expanded: Set[str] = set()
            for uri_str in selected.selected:
                expanded.update(desc_map.get(uri_str, frozenset({uri_str})))
            effective_selected = list(expanded)

        if within_op == "AND":
            # Each selected value must be present — chain separate .filter() calls
            group_qs = qs  # start from base queryset for this group
            for value_str in effective_selected:
                pks = reverse_map.get(value_str, set())
                if not pks:
                    return set()  # impossible to satisfy AND with a missing value
                group_qs = _apply_single_value(group_qs, facet, mapping, pks)
            return set(group_qs.values_list("pk", flat=True))
        else:
            # OR: union all vocab PKs, apply one filter
            pk_union: Set[int] = set()
            for value_str in effective_selected:
                pk_union |= reverse_map.get(value_str, set())
            if not pk_union:
                return set()
            group_qs = _apply_single_value(qs, facet, mapping, pk_union)
            return set(group_qs.values_list("pk", flat=True))

    # Compute PK sets per facet group
    group_pk_sets = []
    for selected in selected_list:
        result = _group_pks(selected)
        if result is None:
            continue  # unknown facet — skip
        group_pk_sets.append(result)

    if not group_pk_sets:
        return qs

    # Combine groups with cross-facet operators
    combined_pks = group_pk_sets[0]
    for i, pk_set in enumerate(group_pk_sets[1:]):
        op = cross_ops[i] if i < len(cross_ops) else "AND"
        if op.upper() == "OR":
            combined_pks = combined_pks | pk_set
        else:
            combined_pks = combined_pks & pk_set

    return qs.filter(pk__in=combined_pks)


def _extract_active_value_strings(
    request: ItemSearchRequest,
) -> Dict[FacetObject, Set[str]]:
    """Return {facet: {selected_value_strings}} for building active flags.

    Mirrors the logic of extract_active_facets_from_selected_facets but returns
    raw value strings rather than rdflib Nodes so they can be compared cheaply
    against the str(item_key) values used in _build_facets.
    """
    result: Dict[FacetObject, Set[str]] = {}
    for selected in request.selectedFacets or []:
        facet = _ITEM_SEARCH_FACETS_MAPPED_BY_KEY.get(URIRef(selected.key))
        if facet is None:
            continue
        result.setdefault(facet, set()).update(selected.selected)
    return result


# ---------------------------------------------------------------------------
# Row → Resource dataclass mapping
# ---------------------------------------------------------------------------


def _map_page(contents: list) -> List[Resource]:
    """Map a list of ResourceContent instances to Resource dataclasses."""
    from curation.models import ViewEvent

    resource_uuids = [str(c.resource.uuid) for c in contents]
    view_counts = (
        {
            str(row["resource_uuid"]): row["cnt"]
            for row in ViewEvent.objects.filter(resource_uuid__in=resource_uuids)
            .values("resource_uuid")
            .annotate(cnt=Count("id"))
        }
        if resource_uuids
        else {}
    )

    resources = []
    for content in contents:
        try:
            resource = _map_content(content)
            resource.views = view_counts.get(str(content.resource.uuid), 0)
            resources.append(resource)
        except Exception:
            logger.warning(
                "postgres_search: failed to map ResourceContent pk=%r; skipping",
                getattr(content, "pk", "?"),
                exc_info=True,
            )
    return resources


def _map_content(content: ResourceContent) -> Resource:
    """Map a single ResourceContent to a Resource dataclass."""
    title = content.title or ""
    resource_id = str(content.resource.uuid)

    # Authors: persons first (SortedM2M preserves order), then organisations.
    authors = []
    for p in content.people.all():
        authors.append(
            PersonAuthor(
                firstname=p.first_name,
                lastname=p.last_name,
                orcid=(p.orcid or None),
            )
        )
    for o in content.organizations.all():
        authors.append(OrganizationAuthor(name=o.name))

    # Communities — deduplicated by pk (same community may have both supporting + recommending relations).
    communities = []
    seen_community_pks = set()
    for rel in content.community_relations.all():
        c = rel.community
        if c is None or c.pk in seen_community_pks:
            continue
        seen_community_pks.add(c.pk)
        communities.append(
            Community(
                id=str(c.uuid),
                slug=getattr(c, "slug", None) or None,
                title=c.title,  # Community.title is the CharField display name
                url=(c.uri or None) or None,
            )
        )

    # Tags.
    tags = [t.name for t in content.keywords.all()]

    # Vocabulary list fields → LabelValueItem.
    learning_resource_types = _to_label_value_items(
        LEARNING_RESOURCE_TYPE_FACET, content.learning_resource_types.all()
    )
    media_types = _to_label_value_items(MEDIA_TYPE_FACET, content.media_types.all())
    disciplines = _to_label_value_items(DISCIPLINE_FACET, content.disciplines.all())
    target_groups = _to_label_value_items(TARGET_AUDIENCE_FACET, content.target_groups.all())
    proficiency_levels = _to_label_value_items(
        PROFICIENCY_LEVEL_FACET, content.proficiency_levels.all()
    )

    # Format: join all file_format display strings with ", ".
    # resolve_facet_value returns the canonical key (e.g. "PDF") for known formats;
    # for unknown formats, clean the raw label: strip leading dots and uppercase.
    format_str: Optional[str] = None
    file_formats_qs = list(content.file_formats.all())
    if file_formats_qs:
        parts = [
            resolve_facet_value(FILE_FORMAT_FACET, ff)
            or (ff.label or "").strip().lstrip(".").upper()
            for ff in file_formats_qs
        ]
        format_str = ", ".join(p for p in parts if p) or None

    # License: first license row, or None.
    license_obj: Optional[License] = None
    licenses_qs = list(content.licenses.all())
    if licenses_qs:
        lc = licenses_qs[0]
        license_obj = License(
            id=lc.spdx_id or "",
            name=lc.label,
            link=(lc.uri or None) or None,
        )

    # Publication date.
    pub_date: Optional[str] = None
    if content.publication_date is not None:
        pub_date = content.publication_date.isoformat()

    # Additional links (ResourceLink reverse = "links").
    links = [link.url for link in content.links.all()]

    # Languages — human labels (display list, not facet-value URIs).
    languages = [lang.label for lang in content.languages.all()]

    # File size.
    file_size: Optional[str] = None
    if content.size_mb is not None:
        file_size = f"{content.size_mb} MB"

    related_works = [
        RelatedWork(
            type=LabelValueItem(label=ri.relation_type.label, value=ri.relation_type.code),
            link=ri.target_url,
        )
        for ri in content.related_items.order_by("order").all()
    ]

    return Resource(
        # BaseItem
        id=resource_id,
        slug=slugify(title) or resource_id,
        title=title,
        description=content.description or "",
        url=content.main_url,
        image=None,
        likes=0,
        views=0,
        comments=0,
        tags=tags,
        authors=authors or [],
        communities=communities or [],
        # ResourceSpecial
        learning_resource_types=learning_resource_types or [],
        media_types=media_types or [],
        disciplines=disciplines or [],
        target_groups=target_groups or [],
        proficiency_levels=proficiency_levels or [],
        format=format_str,
        license=license_obj,
        publication_date=pub_date,
        links=links or [],
        languages=languages or [],
        file_size=file_size,
        publisher=None,
        doi=None,
        learning_time=None,
        versions=None,
        source="postgres",
        related_works=related_works or [],
    )


def _to_label_value_items(facet: FacetObject, instances) -> List[LabelValueItem]:
    """Convert a vocab M2M queryset to a list of LabelValueItem dataclasses.

    Uses canonical facet values from resolve_facet_value; falls back to
    instance.uri then empty string so the field is always a str.
    """
    canonical_labels = {str(k): v for k, v in facet.items.items()}
    items = []
    for v in instances:
        value = resolve_facet_value(facet, v) or getattr(v, "uri", "") or ""
        raw = v.label or ""
        label = (
            canonical_labels.get(value)
            or " ".join(w[0].upper() + w[1:] if w else w for w in raw.split())
            or raw
        )
        items.append(LabelValueItem(label=label, value=value))
    return items


# ---------------------------------------------------------------------------
# Facet compilation
# ---------------------------------------------------------------------------


def _build_discipline_aggregate_map():
    """Return (uri_to_root, top_level_has_children).

    uri_to_root: maps every discipline URI to its top-level ancestor URI.
    top_level_has_children: set of top-level URIs that have at least one sub-discipline.

    Uses select_related up to 3 levels deep to avoid N+1 queries.
    """
    from curation.models import Discipline as DisciplineModel

    uri_to_root = {}
    top_level_has_children = set()

    all_discs = list(
        DisciplineModel.objects.filter(is_active=True)
        .select_related("parent_id__parent_id__parent_id")
        .only(
            "uri",
            "parent_id__uri",
            "parent_id__parent_id__uri",
            "parent_id__parent_id__parent_id__uri",
            "parent_id_id",
            "parent_id__parent_id_id",
            "parent_id__parent_id__parent_id_id",
        )
    )

    for d in all_discs:
        if d.parent_id_id is None:
            uri_to_root[d.uri] = d.uri
        elif d.parent_id.parent_id_id is None:
            uri_to_root[d.uri] = d.parent_id.uri
            top_level_has_children.add(d.parent_id.uri)
        elif d.parent_id.parent_id.parent_id_id is None:
            uri_to_root[d.uri] = d.parent_id.parent_id.uri
            top_level_has_children.add(d.parent_id.parent_id.uri)
        else:
            # 4+ levels: walk up
            current = d.parent_id.parent_id.parent_id
            while current.parent_id_id is not None:
                current = current.parent_id
            uri_to_root[d.uri] = current.uri
            top_level_has_children.add(current.uri)

    return uri_to_root, top_level_has_children


_disc_ancestors_cache = None


def _get_disc_ancestors_map():
    """Cached map: {disc_uri_str: frozenset of ancestor URI strings (including self)}.

    Used for discipline facet ancestor roll-up: when a resource is tagged with
    a sub-discipline, count it toward all ancestor disciplines too.
    Cache persists per worker process; cleared on restart.
    """
    global _disc_ancestors_cache
    if _disc_ancestors_cache is not None:
        return _disc_ancestors_cache

    from curation.models import Discipline as DModel

    disc_data = list(DModel.objects.filter(is_active=True).values("uri", "parent_id__uri"))
    parent_uri_map = {row["uri"]: row["parent_id__uri"] for row in disc_data}

    def _ancestors(uri):
        result = {uri}
        current = uri
        visited = set()
        while True:
            if current in visited:
                break
            visited.add(current)
            parent = parent_uri_map.get(current)
            if not parent:
                break
            result.add(parent)
            current = parent
        return frozenset(result)

    _disc_ancestors_cache = {uri: _ancestors(uri) for uri in parent_uri_map}
    return _disc_ancestors_cache


_disc_descendants_cache = None


def _get_disc_descendants_map():
    """Cached map: {disc_uri_str: frozenset of all descendant URI strings (including self)}.

    Used in _apply_facet_filters to expand a selected discipline to all its sub-disciplines.
    """
    global _disc_descendants_cache
    if _disc_descendants_cache is not None:
        return _disc_descendants_cache

    from collections import defaultdict as _dd

    ancestors_map = _get_disc_ancestors_map()
    descendants: dict = _dd(set)
    for child_uri, anc_set in ancestors_map.items():
        for anc_uri in anc_set:
            descendants[anc_uri].add(child_uri)
    _disc_descendants_cache = {uri: frozenset(descs) for uri, descs in descendants.items()}
    return _disc_descendants_cache


def _build_facets(
    filtered_qs,
    active_values_by_facet: Dict[FacetObject, Set[str]],
) -> List[Facet]:
    """Build the 9 standard facets with counts over the filtered queryset.

    Mirrors the shape of _compile_facets_with_counts: all facet items are
    present (including zero-count), ``active`` is True when the value string
    appears in selectedFacets, ``count`` is the number of result rows that
    carry that facet value.  Facet order follows _ITEM_SEARCH_FACETS.

    Iterates the filtered queryset in Python with the light prefetch graph
    (vocab M2Ms + community_relations__community).  Acceptable at current
    scale; future work could push counts to DB aggregation.
    """
    # Count canonical value strings per facet across all result rows.
    counters: Dict[FacetObject, Counter] = {f: Counter() for f in _ITEM_SEARCH_FACETS}
    # Pre-load ALL active PG communities so the Community facet always shows
    # all of them, even when they have zero results in the current search.
    # This mirrors the /communities/ endpoint which returns Community.objects.all().
    # Load all 137 active PG communities (uri OR uuid-based-uri fallback).
    community_labels: Dict[str, str] = {}
    for _c in CommunityORM.objects.filter(is_active=True).only("pk", "uri", "uuid", "title"):
        _val = resolve_facet_value(COMMUNITY_FACET, _c)
        if _val is not None:
            community_labels[_val] = _c.title

    from collections import defaultdict as _defaultdict

    _disc_to_pks: dict = _defaultdict(set)
    _ancestors_map = _get_disc_ancestors_map()

    for content in filtered_qs:
        # Vocabulary-backed facets.
        for facet, attr in _FACET_TO_SPECIAL_ATTR.items():
            for instance in getattr(content, attr).all():
                val = resolve_facet_value(facet, instance)
                if val is not None:
                    if facet is DISCIPLINE_FACET:
                        for anc_uri in _ancestors_map.get(val, frozenset({val})):
                            _disc_to_pks[anc_uri].add(content.pk)
                    else:
                        counters[facet][val] += 1

        # LICENSE — not in _FACET_TO_SPECIAL_ATTR (special resolver).
        for lc in content.licenses.all():
            val = resolve_facet_value(LICENSE_FACET, lc)
            if val is not None:
                counters[LICENSE_FACET][val] += 1

        # FILE_FORMAT — label-based resolver.
        for ff in content.file_formats.all():
            val = resolve_facet_value(FILE_FORMAT_FACET, ff)
            if val is not None:
                counters[FILE_FORMAT_FACET][val] += 1

        # COMMUNITY — deduplicated by pk to avoid double-counting supporting+recommending relations.
        # Also collects uri->title mapping so facet items can include all communities, not just
        # the 37 in the hardcoded COMMUNITY_FACET.items dict.
        seen_community_pks_facet = set()
        for rel in content.community_relations.all():
            c = rel.community
            if c is None or c.pk in seen_community_pks_facet:
                continue
            seen_community_pks_facet.add(c.pk)
            val = resolve_facet_value(COMMUNITY_FACET, c)
            if val is not None:
                counters[COMMUNITY_FACET][val] += 1
                if val not in community_labels:
                    community_labels[val] = c.title

    # Apply discipline ancestor roll-up: count distinct resource PKs per discipline
    for _uri_str, _pk_set in _disc_to_pks.items():
        counters[DISCIPLINE_FACET][_uri_str] = len(_pk_set)

    # Compile into Facet dataclasses in _ITEM_SEARCH_FACETS order.
    facets = []
    for facet_obj in _ITEM_SEARCH_FACETS:
        counter = counters[facet_obj]
        active_strs = active_values_by_facet.get(facet_obj, set())

        if facet_obj is COMMUNITY_FACET:
            # All active PG community URIs + any that appear in current results or are selected.
            all_uris = set(community_labels.keys()) | set(counter.keys()) | active_strs
            facet_items = sorted(
                [
                    FacetItem(
                        label=community_labels.get(uri, uri.split("/")[-1]),
                        value=uri,
                        active=uri in active_strs,
                        count=counter.get(uri, 0),
                    )
                    for uri in all_uris
                ],
                key=lambda fi: fi.label.lower(),
            )
        else:
            if facet_obj is DISCIPLINE_FACET:
                _, top_level_has_children = _build_discipline_aggregate_map()
                facet_items = []
                for item_key, item_label in facet_obj.items.items():
                    item_key_str = str(item_key)
                    facet_items.append(
                        FacetItem(
                            label=item_label,
                            value=item_key_str,
                            active=item_key_str in active_strs,
                            count=counter.get(item_key_str, 0),
                            hasChildren=item_key_str in top_level_has_children,
                        )
                    )
            else:
                facet_items = []
                for item_key, item_label in facet_obj.items.items():
                    item_key_str = str(item_key)
                    facet_items.append(
                        FacetItem(
                            label=item_label,
                            value=item_key_str,
                            active=item_key_str in active_strs,
                            count=counter.get(item_key_str, 0),
                        )
                    )
            # For DISCIPLINE_FACET: attach active sub-disciplines as children
            if facet_obj is DISCIPLINE_FACET and active_strs:
                from curation.models import Discipline as DisciplineModel

                top_level_uris = {str(k) for k in facet_obj.items.keys()}
                for active_uri in active_strs:
                    if active_uri in top_level_uris:
                        continue
                    try:
                        disc = DisciplineModel.objects.get(uri=active_uri)
                        root = disc
                        for _ in range(5):
                            if root.parent_id_id is None:
                                break
                            root = DisciplineModel.objects.get(pk=root.parent_id_id)
                        root_uri = root.uri
                    except DisciplineModel.DoesNotExist:
                        continue
                    for fi in facet_items:
                        if fi.value == root_uri:
                            if fi.children is None:
                                fi.children = []
                            fi.children.append(
                                FacetItem(
                                    label=disc.label,
                                    value=active_uri,
                                    active=True,
                                    count=counter.get(active_uri, 0),
                                )
                            )
                            break

        facet = Facet()
        facet.facetCategory = FacetCategory(
            label=facet_obj.label,
            name=str(facet_obj.key),
        )
        facet.facetItems = facet_items
        facets.append(facet)

    return facets


# ---------------------------------------------------------------------------
# Candidate interface for multi-source merge (used only by the coordinator)
# ---------------------------------------------------------------------------


def postgres_candidates(request):
    """Return (candidates, facets) for the multi-source merge path.

    Runs the same filtering as postgres_search but skips pagination and the
    heavy prefetch.  Returns a list of Candidate dataclasses
    (uuid, sort_key, source="postgres", ref=None) and the 9 standard facets.

    The Candidate type is imported lazily to avoid a circular import
    (comprehensive_search imports this module; this module must not import
    comprehensive_search at module level).
    """
    from search.query.items.search.comprehensive_search import Candidate, _normalize_sort_key

    filtered = _base_queryset()
    filtered = _apply_date_filters(filtered, request)
    filtered = _apply_facet_filters(filtered, request)
    filtered, _fts_active = _apply_text_query(filtered, request.query)

    active_values_by_facet = _extract_active_value_strings(request)
    facets = _build_facets(filtered, active_values_by_facet)

    candidates = []
    for uuid_val, pub_date in filtered.values_list("resource__uuid", "publication_date"):
        uuid_str = str(uuid_val)
        # publication_date is a DateField matching schema:datePublished used by Fuseki.
        if pub_date is not None:
            raw = pub_date.isoformat()
        else:
            raw = ""
        candidates.append(
            Candidate(
                uuid=uuid_str,
                sort_key=_normalize_sort_key(raw),
                source="postgres",
                ref=None,
            )
        )

    return candidates, facets


def postgres_facets(request, only_uuids=None):
    """Compute facets for the postgres candidate set, restricted to a UUID subset.

    Used by the multi-source merge coordinator (_merge_sources) to build
    dedup-correct facet counts: when fuseki and postgres hold some of the same
    UUIDs, postgres should contribute facet counts only for the UUIDs it
    actually owns in the deduped result (i.e. those NOT also in fuseki).

    Parameters
    ----------
    request : ItemSearchRequest
        The original search request -- used to rebuild the same filtered queryset
        (date filters, facet filters, text query) that postgres_candidates used.
    only_uuids : set[str] | None
        When provided, the queryset is further filtered to only these UUIDs
        before counting.  When None the full filtered set is used (identical
        to the counts already computed inside postgres_candidates).

    Returns
    -------
    list[Facet]
        The 9 standard facets with counts, in _ITEM_SEARCH_FACETS order.
    """
    filtered = _base_queryset()
    filtered = _apply_date_filters(filtered, request)
    filtered = _apply_facet_filters(filtered, request)
    filtered, _fts_active = _apply_text_query(filtered, request.query)

    if only_uuids is not None:
        filtered = filtered.filter(resource__uuid__in=only_uuids)

    active_values_by_facet = _extract_active_value_strings(request)
    return _build_facets(filtered, active_values_by_facet)


def postgres_hydrate(uuids):
    """Hydrate a page of UUIDs into Resource dataclasses.

    Fetches the heavy prefetch graph (authors, keywords, links) only for the
    given uuids — mirrors the page-slice step in postgres_search.  Order of
    the returned list does not matter; the coordinator reorders by the merged
    candidate order.
    """
    if not uuids:
        return []

    qs = (
        ResourceContent.objects.filter(
            is_active=True,
            resource__is_published=True,
            resource__is_removed=False,
            resource__uuid__in=uuids,
        )
        .select_related("resource")
        .prefetch_related(
            "learning_resource_types",
            "disciplines",
            "licenses",
            "proficiency_levels",
            "target_groups",
            "file_formats",
            "media_types",
            "languages",
            "community_relations__community",
            "people",
            "organizations",
            "keywords",
            "links",
            "related_items__relation_type",
        )
    )
    return _map_page(list(qs))
