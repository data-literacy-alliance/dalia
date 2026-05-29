"""
Comprehensive search implementation using split query approach.

This module implements an optimized search pattern:
1. First query fetches matching URIs only (no cartesian product)
2. Parallel SPARQL queries calculate facet counts using GROUP BY
3. Python handles pagination and metadata fetching

Performance: Eliminates cartesian product explosion from OPTIONAL joins.
"""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
from dataclasses import dataclass

from rdflib import DCTERMS, Variable
from rdflib.term import Node, URIRef

from search.api_models.api_models import (
    Facet,
    FacetCategory,
    FacetItem,
    ItemSearchRequest,
    ItemSearchResult,
)
from search.query.items.facets.active_facets_extraction import extract_active_facets_from_selected_facets
from search.query.items.facets.facet_objects import (
    COMMUNITY_FACET,
    FacetObject,
)
from search.query.items.search.text_search import (
    _ITEM_SEARCH_FACETS,
    _ITEM_SEARCH_FACETS_MAPPED_BY_KEY,
)
from search.query.items.search.text_search_query import prepare_where_for_text_search_for_learning_resources
from search.query.items.metadata.items import get_metadata_for_learning_resources
from search.query.utils import query_dalia_dataset
from search.query_builder.query_builder import (
    GROUP,
    UNION,
    VALUES,
    Aggregates,
    QueryBuilder,
)
from search.rdf.namespace import (
    MoDalia,
    fabio,
)


def search_items_comprehensive(request: ItemSearchRequest) -> ItemSearchResult:
    """
    Optimized search using split query approach.

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
    date_published_after = getattr(request, 'datePublished_after', None)
    date_published_before = getattr(request, 'datePublished_before', None)

    active_facets = extract_active_facets_from_selected_facets(
        selected_facets, _ITEM_SEARCH_FACETS_MAPPED_BY_KEY
    )

    # Step 1: Get matching URIs only (no OPTIONAL joins = no cartesian product)
    all_uris = _get_matching_uris(
        text_query, active_facets, sort_by, sort_order,
        date_published_after, date_published_before
    )

    # Step 2: Fetch all facet values for the result URIs and count in Python
    facet_counts = _fetch_and_count_facets_from_results(all_uris)

    # Step 3: Paginate in memory
    total_count = len(all_uris)
    paginated_uris = all_uris[offset:offset + limit]

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

    builder = QueryBuilder().SELECT(
        var_lr,
        distinct=True,
    ).WHERE(
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

    if sort_by == "relevance":
        from search.query_builder.query_builder import FunctionExpressions
        sort_fn = FunctionExpressions.DESC if sort_order == "dsc" else FunctionExpressions.ASC
        builder.ORDER_BY(sort_fn(var_score))
    elif sort_by == "created":
        from search.query_builder.query_builder import FunctionExpressions
        from search.rdf.namespace.xpath_functions import day_from_date, month_from_date, year_from_date
        sort_fn = FunctionExpressions.DESC if sort_order == "dsc" else FunctionExpressions.ASC
        builder.ORDER_BY(
            sort_fn(FunctionExpressions(year_from_date, var_created)),
            sort_fn(FunctionExpressions(month_from_date, var_created)),
            sort_fn(FunctionExpressions(day_from_date, var_created))
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


def _fetch_and_count_facets_from_results(
    all_uris: List[URIRef]
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

    # Mapping from facet to its predicate(s) — note: dalia20 uses hasCommunity
    COMMUNITY_PREDICATE = URIRef("https://dalia.education/hasCommunity")
    facet_predicates = {
        TARGET_AUDIENCE_FACET: [MoDalia.hasTargetGroup],
        MEDIA_TYPE_FACET: [MoDalia.hasMediaType],
        LEARNING_RESOURCE_TYPE_FACET: [MoDalia.hasLearningType],
        LANGUAGE_FACET: [DCTERMS.language],
        PROFICIENCY_LEVEL_FACET: [MoDalia.requiresProficiencyLevel],
        DISCIPLINE_FACET: [fabio.hasDiscipline],
        LICENSE_FACET: [DCTERMS.license],
        FILE_FORMAT_FACET: [DCTERMS.format],
        COMMUNITY_FACET: [COMMUNITY_PREDICATE],
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
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to fetch facet values for {facet.label}: {e}")

    return {facet: dict(counter) for facet, counter in counts.items()}


def _fetch_facet_values(
    uris: List[URIRef],
    predicates: List[URIRef]
) -> List[Node]:
    """
    Fetch all values for the given predicates across all URIs.
    Returns a list of values (may contain duplicates if multiple URIs have same value).
    """
    var_lr = Variable("lr")
    var_value = Variable("value")

    if len(predicates) == 1:
        where_clause = [
            VALUES([var_lr], [(uri,) for uri in uris]),
            (var_lr, predicates[0], var_value)
        ]
    else:
        where_clause = [
            VALUES([var_lr], [(uri,) for uri in uris]),
            GROUP((var_lr, predicates[0], var_value)),
        ]
        for pred in predicates[1:]:
            where_clause.append(UNION((var_lr, pred, var_value)))

    query = QueryBuilder().SELECT(var_value).WHERE(*where_clause).build()
    results = query_dalia_dataset(query)

    return [row.value for row in results]


def _compile_facets_with_counts(
    facet_counts: Dict[FacetObject, Dict[Node, int]],
    active_facets: Dict[FacetObject, List[Node]]
) -> List[Facet]:
    """
    Compile facets with counts for frontend.
    Shows ALL options (including zero-count ones).
    Uses string-based comparison to handle type/datatype mismatches.
    """
    facets = []

    for facet_obj in _ITEM_SEARCH_FACETS:
        counts = facet_counts.get(facet_obj, {})
        active_items = active_facets.get(facet_obj, [])

        # String-based lookup handles type mismatches (e.g. Literal("PDF") vs Literal("PDF", datatype=...))
        counts_by_str = {str(k): v for k, v in counts.items()}
        active_items_str = {str(a) for a in active_items}

        facet_items = []
        for item_key, item_label in facet_obj.items.items():
            item_key_str = str(item_key)
            count = counts_by_str.get(item_key_str, 0)
            is_active = item_key_str in active_items_str

            facet_items.append(
                FacetItem(
                    label=item_label,
                    value=item_key_str,
                    active=is_active,
                    count=count
                )
            )

        facet = Facet()
        facet.facetCategory = FacetCategory(
            label=facet_obj.label,
            name=str(facet_obj.key)
        )
        facet.facetItems = facet_items
        facets.append(facet)

    return facets
