from typing import List

from rdflib import BNode, Graph, Literal, Variable
from rdflib.collection import Collection

from search.api_models.api_models import (
    CurationSuggestPaginatedResult,
    CurationSuggestSearchRequest,
    LabelValueItem,
)
from search.query.utils import filter_by_lang, query_ontologies_dataset
from search.query_builder.query_builder import Aggregates, BIND, FunctionExpressions, OPTIONAL, QueryBuilder
from search.rdf.namespace import Jena_text, SKOS_last_call, lvont


# data for endpoint /curation/suggest/languages
def get_languages_suggestions(request: CurationSuggestSearchRequest) -> CurationSuggestPaginatedResult:
    query = request.q + "*"
    limit = request.limit
    offset = request.offset

    return CurationSuggestPaginatedResult(
        count=count_results_from_languages_search(query),
        offset=offset,
        limit=limit,
        results=_search_languages_and_retrieve_labels(query, limit, offset)
    )


_VARIABLES = {
    "lang": Variable("lang"),
    "label": Variable("label"),
}


def _where_for_text_search(query: str, var_lang: Variable, var_score: Variable, var_label: Variable):
    subject_list_for_text_search = Collection(Graph(), BNode(), [var_lang, var_score, var_label])
    object_list_for_text_search = Collection(Graph(), BNode(), [SKOS_last_call.prefLabel, Literal(query)])

    where = [
        (subject_list_for_text_search, Jena_text.query, object_list_for_text_search),
        filter_by_lang(var_label),
    ]

    return tuple(where)


def prepare_query_for_language_search_and_label_retrieval(query: str, limit: int, offset: int) -> str:
    var_lang = _VARIABLES["lang"]
    var_score = Variable("score")
    var_label = _VARIABLES["label"]
    var_iso639P1Code = Variable("iso639P1Code")
    var_boundIso639P1Code = Variable("boundIso639P1Code")

    return QueryBuilder().SELECT(
        *_VARIABLES.values()
    ).WHERE(
        *_where_for_text_search(query, var_lang, var_score, var_label),
        OPTIONAL(
            (var_lang, lvont.iso639P1Code, var_iso639P1Code),
        ),
        # In case of identical text search scores we would like to show languages with ISO639-1 code first, but
        # ?iso639P1Code might be unbound. This causes problems, because in the ORDER BY clause unbound values come first
        # (see https://www.w3.org/TR/sparql11-query/#modOrderBy).
        # The workaround is to bind ?boundIso639P1Code to the boolean "false" in case ?iso639P1Code is unbound. In
        # Apache Jena's SPARQL engine strings have a lower order than booleans in the ORDER BY clause.
        BIND(FunctionExpressions.COALESCE(var_iso639P1Code, Literal(False)), var_boundIso639P1Code),
    ).ORDER_BY(
        FunctionExpressions.DESC(var_score),
        var_boundIso639P1Code,
    ).LIMIT(limit).OFFSET(offset).build()


def prepare_query_for_count_in_language_search(query: str) -> str:
    var_lang = _VARIABLES["lang"]
    var_score = Variable("score")
    var_label = _VARIABLES["label"]

    return QueryBuilder().SELECT(
        count=Aggregates.COUNT(var_lang),
    ).WHERE(
        *_where_for_text_search(query, var_lang, var_score, var_label),
    ).build()


def _search_languages_and_retrieve_labels(query: str, limit: int, offset: int) -> List[LabelValueItem]:
    sparql_query = prepare_query_for_language_search_and_label_retrieval(query, limit, offset)
    results = query_ontologies_dataset(sparql_query)
    return [_process_result_from_metadata_retrieval(result) for result in results]


def _process_result_from_metadata_retrieval(result) -> LabelValueItem:
    return LabelValueItem(
        value=str(result.lang),
        label=str(result.label)
    )


def count_results_from_languages_search(query: str) -> int:
    sparql_query = prepare_query_for_count_in_language_search(query)
    results = query_ontologies_dataset(sparql_query)
    return next(iter(results)).get("count").toPython()
