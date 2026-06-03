from typing import Dict, List

from rdflib import URIRef, Variable
from rdflib.term import Node

from search.api_models.api_models import ItemSearchRequest, ItemSearchResult
from search.query.items.facets.active_facets_extraction import (
    extract_active_facets_from_selected_facets,
)
from search.query.items.facets.facet_objects import (
    COMMUNITY_FACET,
    DISCIPLINE_FACET,
    FILE_FORMAT_FACET,
    FacetObject,
    LANGUAGE_FACET,
    LEARNING_RESOURCE_TYPE_FACET,
    LICENSE_FACET,
    MEDIA_TYPE_FACET,
    PROFICIENCY_LEVEL_FACET,
    TARGET_AUDIENCE_FACET,
)
from search.query.items.metadata.items import get_metadata_for_learning_resources
from search.query.items.search.count import count_results
from search.query.items.search.facets_compilation import compile_facets_for_text_search
from search.query.items.search.text_search_query import (
    prepare_where_for_text_search_for_learning_resources,
)
from search.query.utils import query_dalia_dataset
from search.query_builder.query_builder import FunctionExpressions, QueryBuilder
from search.rdf.namespace.xpath_functions import day_from_date, month_from_date, year_from_date

_ITEM_SEARCH_FACETS = [
    TARGET_AUDIENCE_FACET,
    MEDIA_TYPE_FACET,
    LEARNING_RESOURCE_TYPE_FACET,
    LANGUAGE_FACET,
    PROFICIENCY_LEVEL_FACET,
    DISCIPLINE_FACET,
    LICENSE_FACET,
    FILE_FORMAT_FACET,
    COMMUNITY_FACET,
]
_ITEM_SEARCH_FACETS_MAPPED_BY_KEY = {facet.key: facet for facet in _ITEM_SEARCH_FACETS}


# data for endpoint /items
def search_items(request: ItemSearchRequest) -> ItemSearchResult:
    text_query = request.query or "*"
    selected_facets = request.selectedFacets
    limit = request.limit
    offset = request.offset
    sort_by = request.sortBy
    sort_order = request.sortOrder

    active_facets = extract_active_facets_from_selected_facets(
        selected_facets, _ITEM_SEARCH_FACETS_MAPPED_BY_KEY
    )

    # TODO: Parallelize these calls
    resource_uri_refs = _text_search_for_learning_resources(
        text_query, active_facets, limit, offset, sort_by, sort_order
    )
    count = count_results(text_query, active_facets)

    resources = get_metadata_for_learning_resources(resource_uri_refs)

    search_result = ItemSearchResult()
    search_result.count = count
    search_result.offset = offset
    search_result.limit = limit
    search_result.results = resources
    search_result.facets = compile_facets_for_text_search(
        text_query, active_facets, _ITEM_SEARCH_FACETS
    )

    # indicate 200
    return search_result


def _text_search_for_learning_resources(
    text_query: str,
    active_facets: Dict[FacetObject, List[Node]],
    limit: int,
    offset: int,
    sort_by: str,
    sort_order: str,
) -> List[URIRef]:
    sparql_query = prepare_query_for_text_search_for_learning_resources(
        text_query, active_facets, limit, offset, sort_by, sort_order
    )
    results = query_dalia_dataset(sparql_query)
    return process_results_for_text_search_for_learning_resources(results)


_SORT_ORDER_LOOKUP = {"asc": FunctionExpressions.ASC, "dsc": FunctionExpressions.DESC}

_VARIABLES = {
    "lr": Variable("lr"),
}


def prepare_query_for_text_search_for_learning_resources(
    text_query: str,
    active_facets: Dict[FacetObject, List[Node]],
    limit: int,
    offset: int,
    sort_by: str,
    sort_order: str,
) -> str:
    var_lr = _VARIABLES["lr"]
    var_score = Variable("score")
    var_created = Variable("created")

    builder = (
        QueryBuilder()
        .SELECT(var_lr, distinct=True)
        .WHERE(
            *prepare_where_for_text_search_for_learning_resources(
                text_query, active_facets, var_lr, var_score, var_created
            )
        )
    )

    sort_order_fn = _SORT_ORDER_LOOKUP[sort_order]
    if sort_by == "relevance":
        builder.ORDER_BY(sort_order_fn(var_score))
    elif sort_by == "created":
        builder.ORDER_BY(
            sort_order_fn(FunctionExpressions(year_from_date, var_created)),
            sort_order_fn(FunctionExpressions(month_from_date, var_created)),
            sort_order_fn(FunctionExpressions(day_from_date, var_created)),
        )

    return builder.LIMIT(limit).OFFSET(offset).build()


def process_results_for_text_search_for_learning_resources(results) -> List[URIRef]:
    return [result.lr for result in results]
