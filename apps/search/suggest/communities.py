from typing import List

from rdflib import BNode, DCTERMS, Graph, Literal, RDF, Variable
from rdflib.collection import Collection

from search.api_models.api_models import (
    CurationSuggestPaginatedResult,
    CurationSuggestSearchRequest,
    LabelValueItem,
)
from search.query.utils import query_dalia_dataset
from search.query_builder.query_builder import Aggregates, FunctionExpressions, QueryBuilder
from search.rdf.namespace import Jena_text, MoDalia


# data for endpoint /curation/suggest/community
def get_communities_suggestions(
    request: CurationSuggestSearchRequest,
) -> CurationSuggestPaginatedResult:
    query = "*" + request.q + "*"
    limit = request.limit
    offset = request.offset

    return CurationSuggestPaginatedResult(
        count=count_results_from_community_search(query),
        offset=offset,
        limit=limit,
        results=_search_communities_and_retrieve_titles(query, limit, offset),
    )


_VARIABLES = {
    "community": Variable("community"),
    "title": Variable("title"),
}


def _where_for_text_search(query: str, var_community: Variable, var_score: Variable):
    subject_list_for_text_search = Collection(Graph(), BNode(), [var_community, var_score])
    object_list_for_text_search = Collection(Graph(), BNode(), [DCTERMS.title, Literal(query)])

    where = [
        (subject_list_for_text_search, Jena_text.query, object_list_for_text_search),
        (var_community, RDF.type, MoDalia.Community),
    ]

    return tuple(where)


def prepare_query_for_community_search_and_title_retrieval(
    query: str, limit: int, offset: int
) -> str:
    var_community = _VARIABLES["community"]
    var_score = Variable("score")

    return (
        QueryBuilder()
        .SELECT(*_VARIABLES.values())
        .WHERE(
            QueryBuilder()
            .SELECT(var_community, distinct=True)
            .WHERE(*_where_for_text_search(query, var_community, var_score))
            .ORDER_BY(FunctionExpressions.DESC(var_score))
            .LIMIT(limit)
            .OFFSET(offset)
            .build(),
            (var_community, DCTERMS.title, _VARIABLES["title"]),
        )
        .build()
    )


def prepare_query_for_count_in_community_search(query: str) -> str:
    var_community = _VARIABLES["community"]
    var_score = Variable("score")

    return (
        QueryBuilder()
        .SELECT(
            count=Aggregates("COUNT", var_community, ["DISTINCT"]),
        )
        .WHERE(*_where_for_text_search(query, var_community, var_score))
        .build()
    )


def _search_communities_and_retrieve_titles(
    query: str, limit: int, offset: int
) -> List[LabelValueItem]:
    sparql_query = prepare_query_for_community_search_and_title_retrieval(query, limit, offset)
    results = query_dalia_dataset(sparql_query)

    return [_process_result_from_metadata_retrieval(result) for result in results]


def _process_result_from_metadata_retrieval(result) -> LabelValueItem:
    return LabelValueItem(value=str(result.community), label=str(result.title))


def count_results_from_community_search(query: str) -> int:
    sparql_query = prepare_query_for_count_in_community_search(query)
    results = query_dalia_dataset(sparql_query)
    return next(iter(results)).get("count").toPython()
