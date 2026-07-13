"""
Comprehensive search implementation using split query approach.

This module implements an optimized search pattern:
1. First query fetches matching URIs only (no cartesian product)
2. Parallel SPARQL queries calculate facet counts using GROUP BY
3. Python handles pagination and metadata fetching

Performance: Eliminates cartesian product explosion from OPTIONAL joins.
"""

import logging
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field as dc_field
from typing import Dict, List, Optional

from rdflib import DCTERMS, Variable
from rdflib.term import Node, URIRef

from search.api_models.api_models import (
    Facet,
    FacetCategory,
    FacetItem,
    ItemSearchRequest,
    ItemSearchResult,
)
from search.query.items.facets.active_facets_extraction import (
    extract_active_facets_from_selected_facets,
)
from search.query.items.facets.facet_objects import (
    COMMUNITY_FACET,
    FacetObject,
)
from search.query.items.search.text_search import (
    _ITEM_SEARCH_FACETS,
    _ITEM_SEARCH_FACETS_MAPPED_BY_KEY,
)
from search.query.items.search.text_search_query import (
    prepare_where_for_text_search_for_learning_resources,
)
from search.query.items.metadata.items import get_metadata_for_learning_resources
from search.query.utils import query_dalia_dataset
from search.query_builder.query_builder import (
    GROUP,
    UNION,
    VALUES,
    QueryBuilder,
)
from search.query.items.search.sources import get_enabled_search_sources
from curation.models.communities import Community as CommunityModel
from search.query.communities.one_to_one_metadata import get_one_to_one_metadata_for_communities
from search.rdf.namespace import (
    MoDalia,
    bibframe_lite_relation,
    fabio,
    rec,
)
from search.query.items.search.producers.postgres_producer import (
    postgres_search,
    postgres_candidates,
    postgres_facets as compute_postgres_facets,
    postgres_hydrate,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Candidate dataclass — used only by the multi-source merge path
# ---------------------------------------------------------------------------


@dataclass
class Candidate:
    """Lightweight record for cross-source dedup + sort before hydration.

    sort_key is a normalized YYYY-MM-DD date string (see _normalize_sort_key).
    Cross-source ordering is by this date with uuid as a stable secondary key;
    relevance is NOT used in multi-source mode (documented).
    ref is the URIRef for fuseki candidates (needed for hydration); None for
    postgres (hydrated by uuid string instead).
    """

    uuid: str
    sort_key: str
    source: str  # "fuseki" | "postgres"
    ref: Optional[URIRef] = dc_field(default=None)  # URIRef for fuseki; None for postgres


_DATE_RE = re.compile(r"^(?P<y>\d{4})(?:-(?P<m>\d{2})(?:-(?P<d>\d{2}))?)?")


def _normalize_sort_key(raw: str) -> str:
    """Normalize a date string to YYYY-MM-DD for cross-source comparison.

    Pads missing month/day with -01.  Returns "0000-00-00" if the input is
    empty or cannot be parsed — those items sort last on descending order.
    """
    if not raw:
        return "0000-00-00"
    m = _DATE_RE.match(raw.strip())
    if not m:
        return "0000-00-00"
    y = m.group("y")
    mo = m.group("m") or "01"
    d = m.group("d") or "01"
    return f"{y}-{mo}-{d}"


# ---------------------------------------------------------------------------
# Coordinator
# ---------------------------------------------------------------------------


def search_items_comprehensive(request: ItemSearchRequest) -> ItemSearchResult:
    """Entry point for the item search endpoint.

    Reads the enabled search sources (DALIA_SEARCH_SOURCES) and dispatches to
    the corresponding producers.  With the default ["fuseki"] this returns the
    Fuseki producer's result unchanged (single-source fast path, byte-identical
    to the pre-merge behaviour).

    When more than one source is enabled the multi-source merge path is used:
    candidates are gathered from each source, deduped by UUID (fuseki wins
    collisions), sorted by normalized creation date, paginated, and only the
    page slice is hydrated (heavy metadata is never fetched for off-page items).
    """
    sources = get_enabled_search_sources()

    if len(sources) == 1:
        # Single-source fast path — unchanged from before.
        produced = _run_producer(sources[0], request)
        if produced is not None:
            return produced
        return _empty_search_result(request)

    # Multi-source merge path.
    return _merge_sources(sources, request)


def _merge_sources(sources: List[str], request: ItemSearchRequest) -> ItemSearchResult:
    """Gather candidates from each source, dedup, sort, paginate, then hydrate.

    Precedence for UUID collision resolution: the source that appears first in
    the list wins ("fuseki" is placed first so fuseki wins over postgres when
    both hold the same UUID).

    Facet counts are dedup-correct (S10): each source contributes counts only
    for the UUIDs it *owns* in the deduped set.  Fuseki wins all collisions so
    its facets are reused unchanged.  Postgres owns only the UUIDs not also in
    fuseki; if no overlap exists (today's state) its facets are reused as-is
    (no recompute); if overlap exists, postgres_facets() is called with the
    owned subset to get corrected counts.
    """
    # Step 1: Gather (candidates, facets, all-uuids) from each source.
    # A failing source contributes nothing (logged by the per-source wrapper).
    all_candidates: List[Candidate] = []
    # Per-source raw output: source_name -> (candidates, facets)
    source_output: Dict[str, tuple] = {}

    for source in sources:
        cands, facets = _run_candidates(source, request)
        source_output[source] = (cands, facets)
        all_candidates.extend(cands)

    # Step 2: Dedup by UUID — first occurrence wins (fuseki is first in sources).
    seen_uuids: set = set()
    deduped: List[Candidate] = []
    for c in all_candidates:
        if c.uuid not in seen_uuids:
            seen_uuids.add(c.uuid)
            deduped.append(c)

    # Step 3: Sort — by sort_key (DESC when sortOrder == "dsc" else ASC),
    # secondary key uuid (stable tiebreak).
    reverse_sort = request.sortOrder == "dsc"
    deduped.sort(key=lambda c: c.uuid)  # stable secondary, always ascending
    deduped.sort(key=lambda c: c.sort_key, reverse=reverse_sort)  # primary by date

    # Step 4: Pagination.
    total = len(deduped)
    offset = request.offset
    limit = request.limit
    page: List[Candidate] = deduped[offset : offset + limit]

    # Step 5: Hydrate only the page, grouped by source.
    fuseki_page = [c for c in page if c.source == "fuseki"]
    postgres_page = [c for c in page if c.source == "postgres"]

    hydrated: Dict[str, object] = {}  # uuid -> Resource

    if fuseki_page:
        try:
            fuseki_resources = fuseki_hydrate([c.ref for c in fuseki_page])
            for r in fuseki_resources:
                if r.id:
                    hydrated[r.id] = r
        except Exception:
            logger.exception("fuseki_hydrate failed for page slice; those items omitted.")

    if postgres_page:
        try:
            pg_resources = postgres_hydrate([c.uuid for c in postgres_page])
            for r in pg_resources:
                if r.id:
                    hydrated[r.id] = r
        except Exception:
            logger.exception("postgres_hydrate failed for page slice; those items omitted.")

    # Reassemble in merged sort order (skip any that failed to hydrate).
    results = []
    for c in page:
        r = hydrated.get(c.uuid)
        if r is None:
            logger.warning("Candidate uuid=%r could not be hydrated; omitting.", c.uuid)
        else:
            results.append(r)

    # Step 6: Build dedup-correct facet lists and union them.
    #
    # Ownership rule:
    #   fuseki owns ALL its UUIDs (it has highest precedence; no UUID it holds
    #   was displaced by another source, so its facet counts are unchanged).
    #   postgres owns only the UUIDs NOT also held by fuseki.
    #
    # Build the per-source UUID sets from the raw candidates (before dedup).
    # These are the *full* candidate sets returned by each source, not the
    # post-dedup survivors — ownership is defined as "would have been kept if
    # the other source were absent", which equals "not in the higher-precedence
    # source".
    fuseki_cands, fuseki_facets = source_output.get("fuseki", ([], []))
    postgres_cands, postgres_facets_raw = source_output.get("postgres", ([], []))

    fuseki_uuids: set = {c.uuid for c in fuseki_cands}
    postgres_all_uuids: set = {c.uuid for c in postgres_cands}
    # Postgres owns UUIDs that are NOT in fuseki (fuseki wins collisions).
    owned_postgres_uuids: set = postgres_all_uuids - fuseki_uuids

    dedup_correct_facet_lists: List[List[Facet]] = []

    # Fuseki facets: unchanged — fuseki owns all its candidates.
    if fuseki_facets:
        dedup_correct_facet_lists.append(fuseki_facets)

    # Postgres facets: reuse if no overlap, otherwise recompute over owned subset.
    if postgres_all_uuids:
        if len(owned_postgres_uuids) == len(postgres_all_uuids):
            # No overlap with fuseki — reuse the facets already computed.
            # This is today's state (sources are disjoint).
            if postgres_facets_raw:
                dedup_correct_facet_lists.append(postgres_facets_raw)
        else:
            # Overlap detected — recompute postgres facets over the owned subset
            # only so that displaced UUIDs are not double-counted.
            try:
                corrected = compute_postgres_facets(request, only_uuids=owned_postgres_uuids)
                if corrected:
                    dedup_correct_facet_lists.append(corrected)
            except Exception:
                logger.exception(
                    "postgres_facets recompute failed; falling back to raw postgres facets."
                )
                if postgres_facets_raw:
                    dedup_correct_facet_lists.append(postgres_facets_raw)

    unioned_facets = _union_facets(dedup_correct_facet_lists)

    result = ItemSearchResult()
    result.count = total
    result.offset = offset
    result.limit = limit
    result.results = results
    result.facets = unioned_facets
    return result


def _run_producer(source: str, request: ItemSearchRequest) -> Optional[ItemSearchResult]:
    """Run a single search producer in isolation. Returns its ItemSearchResult,
    or None if the source has no registered producer or the producer raises."""
    producer = _SEARCH_PRODUCERS.get(source)
    if producer is None:
        logger.warning("No producer registered for search source %r; skipping.", source)
        return None
    try:
        return producer(request)
    except Exception:
        logger.exception("Search producer %r failed; contributing no results.", source)
        return None


def _run_candidates(source: str, request: ItemSearchRequest):
    """Run a single candidates function in isolation.

    Returns (candidates, facets).  Returns ([], []) if the source has no
    registered candidates function or if the function raises.
    """
    fn = _CANDIDATE_PRODUCERS.get(source)
    if fn is None:
        logger.warning("No candidates function for search source %r; skipping.", source)
        return [], []
    try:
        return fn(request)
    except Exception:
        logger.exception("Candidates producer %r failed; contributing no results.", source)
        return [], []


def _empty_search_result(request: ItemSearchRequest) -> ItemSearchResult:
    """A valid, empty result (count=0) preserving the requested offset/limit."""
    result = ItemSearchResult()
    result.count = 0
    result.offset = request.offset
    result.limit = request.limit
    result.results = []
    result.facets = []
    return result


# ---------------------------------------------------------------------------
# Fuseki single-source fast path (unchanged)
# ---------------------------------------------------------------------------


def fuseki_search(request: ItemSearchRequest) -> ItemSearchResult:
    """
    Fuseki/SPARQL producer — optimized search using split query approach.

    Process:
    1. Query 1: Get matching URIs only (fast, no cartesian product)
    2. Query 2-10: Calculate facet counts via parallel SPARQL GROUP BY queries
    3. Apply pagination in Python
    4. Fetch metadata for current page
    5. Return results with facet counts
    """
    text_query = request.query or "*"
    selected_facets = request.selectedFacets
    limit = request.limit
    offset = request.offset
    sort_by = request.sortBy
    sort_order = request.sortOrder
    date_published_after = getattr(request, "datePublished_after", None)
    date_published_before = getattr(request, "datePublished_before", None)

    active_facets = extract_active_facets_from_selected_facets(
        selected_facets, _ITEM_SEARCH_FACETS_MAPPED_BY_KEY
    )

    # Step 1: Get matching URIs only (no OPTIONAL joins = no cartesian product)
    all_uris = _get_matching_uris(
        text_query, active_facets, sort_by, sort_order, date_published_after, date_published_before
    )

    # Step 2: Fetch all facet values for the result URIs and count in Python
    facet_counts = _fetch_and_count_facets_from_results(all_uris)

    # Step 3: Paginate in memory
    total_count = len(all_uris)
    paginated_uris = all_uris[offset : offset + limit]

    # Step 4: Fetch metadata only for current page
    resources = get_metadata_for_learning_resources(paginated_uris)

    # Step 5: Compile facets with counts
    facets = _compile_facets_with_counts(facet_counts, active_facets)

    # Build result
    search_result = ItemSearchResult()
    search_result.count = total_count
    search_result.offset = offset
    search_result.limit = limit
    search_result.results = resources
    search_result.facets = facets

    return search_result


# ---------------------------------------------------------------------------
# Fuseki candidate + hydrate interface (used only by the merge path)
# ---------------------------------------------------------------------------


def fuseki_candidates(request: ItemSearchRequest):
    """Return (candidates, facets) for the multi-source merge path.

    Gets all matching (URI, created) pairs without pagination, builds Candidate
    dataclasses with normalized sort keys, and computes facets via the same
    pipeline as fuseki_search.  Does NOT fetch heavy metadata.
    """
    text_query = request.query or "*"
    selected_facets = request.selectedFacets
    sort_by = request.sortBy
    sort_order = request.sortOrder
    date_published_after = getattr(request, "datePublished_after", None)
    date_published_before = getattr(request, "datePublished_before", None)

    active_facets = extract_active_facets_from_selected_facets(
        selected_facets, _ITEM_SEARCH_FACETS_MAPPED_BY_KEY
    )

    uri_created_pairs = _get_matching_uris_with_created(
        text_query, active_facets, sort_by, sort_order, date_published_after, date_published_before
    )

    candidates = []
    for lr, created_node in uri_created_pairs:
        uuid_str = str(lr).split("/")[-1]
        raw_date = str(created_node) if created_node is not None else ""
        # SPARQL date literals may carry datatype suffix (e.g. "2023-04-01"^^xsd:date)
        # Strip after "^^" to get the bare date value.
        if "^^" in raw_date:
            raw_date = raw_date.split("^^")[0].strip("\"'")
        candidates.append(
            Candidate(
                uuid=uuid_str,
                sort_key=_normalize_sort_key(raw_date),
                source="fuseki",
                ref=lr,
            )
        )

    refs = [c.ref for c in candidates]
    facet_counts = _fetch_and_count_facets_from_results(refs)
    facets = _compile_facets_with_counts(facet_counts, active_facets)

    return candidates, facets


def fuseki_hydrate(refs: List[URIRef]) -> List:
    """Hydrate a list of URIRefs into Resource dataclasses via SPARQL.

    Wraps get_metadata_for_learning_resources which already tags source="fuseki"
    via the shared builder.
    """
    if not refs:
        return []
    return get_metadata_for_learning_resources(refs)


# ---------------------------------------------------------------------------
# Producer registries
# ---------------------------------------------------------------------------

# Single-source fast path registry — maps source name → producer callable.
_SEARCH_PRODUCERS = {
    "fuseki": fuseki_search,
    "postgres": postgres_search,
}

# Candidate-interface registry — maps source name → candidates callable.
# Used only by the multi-source merge path.
_CANDIDATE_PRODUCERS = {
    "fuseki": fuseki_candidates,
    "postgres": postgres_candidates,
}


# ---------------------------------------------------------------------------
# Fuseki SPARQL helpers
# ---------------------------------------------------------------------------


def _get_matching_uris(
    text_query: str,
    active_facets: Dict[FacetObject, List[Node]],
    sort_by: str,
    sort_order: str,
    date_published_after: Optional[str] = None,
    date_published_before: Optional[str] = None,
) -> List[URIRef]:
    """
    Get list of matching URIs using a single query WITHOUT facet OPTIONALs.

    This eliminates cartesian product explosion - returns one row per result.
    Uses DISTINCT to avoid duplicate URIs from OPTIONAL branches in text search.
    """
    var_lr = Variable("lr")
    var_score = Variable("score")
    var_created = Variable("created")

    builder = (
        QueryBuilder()
        .SELECT(
            var_lr,
            distinct=True,
        )
        .WHERE(
            *prepare_where_for_text_search_for_learning_resources(
                text_query,
                active_facets,
                var_lr,
                var_score,
                var_created,
                date_published_after,
                date_published_before,
            ),
        )
    )

    if sort_by == "relevance":
        from search.query_builder.query_builder import FunctionExpressions

        sort_fn = FunctionExpressions.DESC if sort_order == "dsc" else FunctionExpressions.ASC
        builder.ORDER_BY(sort_fn(var_score))
    elif sort_by == "created":
        from search.query_builder.query_builder import FunctionExpressions
        from search.rdf.namespace.xpath_functions import (
            day_from_date,
            month_from_date,
            year_from_date,
        )

        sort_fn = FunctionExpressions.DESC if sort_order == "dsc" else FunctionExpressions.ASC
        builder.ORDER_BY(
            sort_fn(FunctionExpressions(year_from_date, var_created)),
            sort_fn(FunctionExpressions(month_from_date, var_created)),
            sort_fn(FunctionExpressions(day_from_date, var_created)),
        )

    query = builder.build()
    results = query_dalia_dataset(query)

    seen = set()
    unique_uris = []
    for row in results:
        if row.lr not in seen:
            seen.add(row.lr)
            unique_uris.append(row.lr)

    return unique_uris


def _get_matching_uris_with_created(
    text_query: str,
    active_facets: Dict[FacetObject, List[Node]],
    sort_by: str,
    sort_order: str,
    date_published_after: Optional[str] = None,
    date_published_before: Optional[str] = None,
) -> List[tuple]:
    """Get list of (URIRef, created_node) pairs for the candidates interface.

    SELECTs DISTINCT ?lr ?created with the same WHERE clause as
    _get_matching_uris.  The created value may be None when not bound (OPTIONAL
    in the WHERE clause).  Ordering is applied for a best-effort ordering of the
    candidate list before dedup; the merge coordinator re-sorts anyway.
    """
    var_lr = Variable("lr")
    var_score = Variable("score")
    var_created = Variable("created")

    builder = (
        QueryBuilder()
        .SELECT(
            var_lr,
            var_created,
            distinct=True,
        )
        .WHERE(
            *prepare_where_for_text_search_for_learning_resources(
                text_query,
                active_facets,
                var_lr,
                var_score,
                var_created,
                date_published_after,
                date_published_before,
            ),
        )
    )

    if sort_by == "relevance":
        from search.query_builder.query_builder import FunctionExpressions

        sort_fn = FunctionExpressions.DESC if sort_order == "dsc" else FunctionExpressions.ASC
        builder.ORDER_BY(sort_fn(var_score))
    elif sort_by == "created":
        from search.query_builder.query_builder import FunctionExpressions
        from search.rdf.namespace.xpath_functions import (
            day_from_date,
            month_from_date,
            year_from_date,
        )

        sort_fn = FunctionExpressions.DESC if sort_order == "dsc" else FunctionExpressions.ASC
        builder.ORDER_BY(
            sort_fn(FunctionExpressions(year_from_date, var_created)),
            sort_fn(FunctionExpressions(month_from_date, var_created)),
            sort_fn(FunctionExpressions(day_from_date, var_created)),
        )

    query = builder.build()
    results = query_dalia_dataset(query)

    seen_uris = set()
    pairs = []
    for row in results:
        if row.lr not in seen_uris:
            seen_uris.add(row.lr)
            created = getattr(row, "created", None)
            pairs.append((row.lr, created))

    return pairs


def _fetch_and_count_facets_from_results(
    all_uris: List[URIRef],
) -> Dict[FacetObject, Dict[Node, int]]:
    """
    Fetch all facet values for the given URIs and count in Python.
    Single SPARQL query fetches all facet values, then Python counts them.
    """
    from search.query.items.facets.facet_objects import (
        TARGET_AUDIENCE_FACET,
        MEDIA_TYPE_FACET,
        LEARNING_RESOURCE_TYPE_FACET,
        LANGUAGE_FACET,
        PROFICIENCY_LEVEL_FACET,
        DISCIPLINE_FACET,
        LICENSE_FACET,
        FILE_FORMAT_FACET,
        COMMUNITY_FACET,
    )

    if not all_uris:
        return {facet: {} for facet in _ITEM_SEARCH_FACETS}

    # Mapping from facet to its predicate(s).
    # Community is linked via rec:recommender (and bflr:supportinghost for future data).
    # hasCommunity was a synthetic predicate with 0 triples in Fuseki (issue #116).
    facet_predicates = {
        TARGET_AUDIENCE_FACET: [MoDalia.hasTargetGroup],
        MEDIA_TYPE_FACET: [MoDalia.hasMediaType],
        LEARNING_RESOURCE_TYPE_FACET: [MoDalia.hasLearningType],
        LANGUAGE_FACET: [DCTERMS.language],
        PROFICIENCY_LEVEL_FACET: [MoDalia.requiresProficiencyLevel],
        DISCIPLINE_FACET: [fabio.hasDiscipline],
        LICENSE_FACET: [DCTERMS.license],
        FILE_FORMAT_FACET: [DCTERMS.format],
        COMMUNITY_FACET: [rec.recommender, bibframe_lite_relation.supportinghost],
    }

    counts = {facet: Counter() for facet in _ITEM_SEARCH_FACETS}

    with ThreadPoolExecutor(max_workers=9) as executor:
        future_to_facet = {}
        for facet, predicates in facet_predicates.items():
            future = executor.submit(_fetch_facet_values, all_uris, predicates)
            future_to_facet[future] = facet

        for future in as_completed(future_to_facet):
            facet = future_to_facet[future]
            try:
                values = future.result()
                for value in values:
                    counts[facet][value] += 1
            except Exception as e:
                logger.error("Failed to fetch facet values for %s: %s", facet.label, e)

    return {facet: dict(counter) for facet, counter in counts.items()}


def _fetch_facet_values(uris: List[URIRef], predicates: List[URIRef]) -> List[Node]:
    """
    Fetch all values for the given predicates across all URIs.
    Returns a list of values (may contain duplicates if multiple URIs have same value).
    """
    var_lr = Variable("lr")
    var_value = Variable("value")

    if len(predicates) == 1:
        where_clause = [
            VALUES([var_lr], [(uri,) for uri in uris]),
            (var_lr, predicates[0], var_value),
        ]
    else:
        where_clause = [
            VALUES([var_lr], [(uri,) for uri in uris]),
            GROUP((var_lr, predicates[0], var_value)),
        ]
        for pred in predicates[1:]:
            where_clause.append(UNION((var_lr, pred, var_value)))

    query = QueryBuilder().SELECT(var_lr, var_value, distinct=True).WHERE(*where_clause).build()
    results = query_dalia_dataset(query)

    return [row.value for row in results]


def _compile_facets_with_counts(
    facet_counts: Dict[FacetObject, Dict[Node, int]], active_facets: Dict[FacetObject, List[Node]]
) -> List[Facet]:
    """
    Compile facets with counts for frontend.
    Shows ALL options (including zero-count ones).
    Uses string-based comparison to handle type/datatype mismatches.
    """
    # Pre-load community labels from PG for dynamic community facet items.
    # Only executed when community counts exist (avoids a DB hit when there are no results).
    _community_label_cache: dict = {}

    facets = []

    for facet_obj in _ITEM_SEARCH_FACETS:
        counts = facet_counts.get(facet_obj, {})
        active_items = active_facets.get(facet_obj, [])

        counts_by_str = {str(k): v for k, v in counts.items()}
        active_items_str = {str(a) for a in active_items}

        if facet_obj is COMMUNITY_FACET:
            # Pre-load ALL active PG communities so the facet shows all of them,
            # even those with zero results in the current search.
            if not _community_label_cache:
                # Load all active PG communities: uri field if set, else uuid-based-uri fallback.
                for _c in CommunityModel.objects.filter(is_active=True).only(
                    "pk", "uri", "uuid", "title"
                ):
                    _uri = (
                        _c.uri or ""
                    ).strip() or f"https://id.dalia.education/community/{_c.uuid}"
                    if _uri:
                        _community_label_cache[_uri] = _c.title
            # Union: all PG communities + any URIs in current results + active selections.
            all_uris = (
                set(_community_label_cache.keys()) | set(counts_by_str.keys()) | active_items_str
            )
            # Fuseki fallback for URIs in results not yet linked to a PG record.
            remaining = [u for u in all_uris if u not in _community_label_cache]
            if remaining:
                from rdflib import URIRef as _URIRef

                fuseki_meta = get_one_to_one_metadata_for_communities(
                    [_URIRef(u) for u in remaining]
                )
                for uri, comm in fuseki_meta.items():
                    if comm.title:
                        _community_label_cache[str(uri)] = comm.title
            facet_items = sorted(
                [
                    FacetItem(
                        label=label,
                        value=uri,
                        active=uri in active_items_str,
                        count=counts_by_str.get(uri, 0),
                    )
                    for uri in all_uris
                    # Only show entries that have a resolvable label (from PG or Fuseki).
                    # Active (selected) URIs are always included so the user can
                    # see and deselect their current filter; UUID used as fallback label.
                    # Unlabelled Fuseki-only ghost communities are excluded entirely.
                    if (label := _community_label_cache.get(uri))
                    or (uri in active_items_str and (label := uri.split("/")[-1]))
                ],
                key=lambda fi: fi.label.lower(),
            )
        else:
            facet_items = []
            for item_key, item_label in facet_obj.items.items():
                item_key_str = str(item_key)
                count = counts_by_str.get(item_key_str, 0)
                is_active = item_key_str in active_items_str
                facet_items.append(
                    FacetItem(label=item_label, value=item_key_str, active=is_active, count=count)
                )

        facet = Facet()
        facet.facetCategory = FacetCategory(label=facet_obj.label, name=str(facet_obj.key))
        facet.facetItems = facet_items
        facets.append(facet)

    return facets


# ---------------------------------------------------------------------------
# Facet union helper (S9 interim; counts made dedup-correct in S10)
# ---------------------------------------------------------------------------


def _union_facets(facet_lists: List[List[Facet]]) -> List[Facet]:
    """Union per-source facet lists into a single list for the merged result.

    Sums counts by (facetCategory.name, facetItem.value); OR's the active
    flag.  Preserves the 9-facet category order defined by _ITEM_SEARCH_FACETS.
    Returns an empty list when no facet lists are provided.

    Note: as of S10 the caller (_merge_sources) passes dedup-correct per-source
    facet lists, so this function only sums and merges; no extra correction needed.
    """
    if not facet_lists:
        return []
    if len(facet_lists) == 1:
        return facet_lists[0]

    # Collect all seen category names in appearance order (first list sets order).
    category_order: List[str] = []
    seen_categories: set = set()

    # Aggregate: category_name -> item_value -> {count, active}
    aggregated: Dict[str, Dict[str, dict]] = {}

    for facet_list in facet_lists:
        for facet in facet_list:
            cat_name = facet.facetCategory.name if facet.facetCategory else ""
            if cat_name not in seen_categories:
                seen_categories.add(cat_name)
                category_order.append(cat_name)
                aggregated[cat_name] = {}

            for item in facet.facetItems or []:
                val = item.value
                if val not in aggregated[cat_name]:
                    aggregated[cat_name][val] = {
                        "label": item.label,
                        "count": 0,
                        "active": False,
                    }
                aggregated[cat_name][val]["count"] += item.count or 0
                aggregated[cat_name][val]["active"] = (
                    aggregated[cat_name][val]["active"] or item.active
                )

    # Enforce canonical facet order defined by _ITEM_SEARCH_FACETS.
    _canonical_order = {str(f.key): i for i, f in enumerate(_ITEM_SEARCH_FACETS)}
    category_order.sort(key=lambda n: _canonical_order.get(n, len(_ITEM_SEARCH_FACETS)))

    # Rebuild Facet objects in canonical category order.
    result: List[Facet] = []
    for cat_name in category_order:
        # Retrieve the category label from the first list that had this category.
        # Default to cat_name so it is never None even if label is missing.
        cat_label = cat_name
        for facet_list in facet_lists:
            for facet in facet_list:
                if facet.facetCategory and facet.facetCategory.name == cat_name:
                    cat_label = facet.facetCategory.label or cat_name
                    break
            else:
                continue
            break

        items_dict = aggregated[cat_name]
        # Preserve item order from the first occurrence of each value.
        facet_items = [
            FacetItem(
                label=data["label"],
                value=val,
                active=data["active"],
                count=data["count"],
            )
            for val, data in items_dict.items()
        ]

        facet = Facet()
        facet.facetCategory = FacetCategory(label=cat_label, name=cat_name)
        facet.facetItems = facet_items
        result.append(facet)

    return result
