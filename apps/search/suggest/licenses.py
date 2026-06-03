from typing import List

from rdflib import BNode, Graph, Literal, RDF, Variable
from rdflib.collection import Collection

from search.api_models.api_models import (
    CurationSuggestLicensesRequest,
    CurationSuggestLicensesResult,
    CurationSuggestLicensesResultItem,
)
from search.query.utils import query_ontologies_dataset
from search.query_builder.query_builder import (
    Aggregates,
    BIND,
    FILTER_EXISTS,
    FunctionExpressions,
    OPTIONAL,
    QueryBuilder,
)
from search.rdf.namespace import Dalia_text, Jena_text, spdx


# data for endpoint /curation/suggest/licenses
def get_licenses_suggestions(
    request: CurationSuggestLicensesRequest,
) -> CurationSuggestLicensesResult:
    license_filter = request.filter

    # TODO: replace with match-case statement (Python 3.10 and above)
    if license_filter == "recommended":
        return _get_recommended_licenses(request)
    elif license_filter == "all":
        return search_all_licenses(request)
    elif license_filter == "recent":
        return _get_recently_used_licenses(request)


_VARIABLES = {
    "license": Variable("license"),
    "licenseId": Variable("licenseId"),
    "licenseName": Variable("licenseName"),
    "licenseLink": Variable("licenseLink"),
    "licenseDescription": Variable("licenseDescription"),
}


def _where_for_text_search(query: str, var_license: Variable, var_score: Variable):
    subject_list_for_text_search = Collection(Graph(), BNode(), [var_license, var_score])
    object_list_for_text_search = Collection(
        Graph(), BNode(), [Dalia_text.spdxLicensesTexts, Literal(query)]
    )

    where = [
        (subject_list_for_text_search, Jena_text.query, object_list_for_text_search),
        (var_license, RDF.type, spdx.ListedLicense),
        FILTER_EXISTS((var_license, spdx.isDeprecatedLicenseId, Literal(True)), state=False),
    ]

    return tuple(where)


def prepare_query_for_license_search_and_metadata_retrieval(
    query: str, limit: int, offset: int
) -> str:
    var_license = _VARIABLES["license"]
    var_score = Variable("score")
    var_license_link_from_crosslink = Variable("licenseLinkFromCrosslink")
    var_crossref = Variable("crossref")
    var_order = Variable("order")

    return (
        QueryBuilder()
        .SELECT(*_VARIABLES.values())
        .WHERE(
            QueryBuilder()
            .SELECT(var_license, distinct=True)
            .WHERE(*_where_for_text_search(query, var_license, var_score))
            .ORDER_BY(FunctionExpressions.DESC(var_score))
            .LIMIT(limit)
            .OFFSET(offset)
            .build(),
            OPTIONAL((var_license, spdx.licenseId, _VARIABLES["licenseId"])),
            OPTIONAL((var_license, spdx.name, _VARIABLES["licenseName"])),
            OPTIONAL(
                QueryBuilder()
                .SELECT(var_license, var_license_link_from_crosslink)
                .WHERE(
                    (var_license, spdx.crossRef_P, var_crossref),
                    (var_crossref, RDF.type, spdx.CrossRef_T),
                    (var_crossref, spdx.order, var_order),
                    (var_crossref, spdx.url, var_license_link_from_crosslink),
                )
                .ORDER_BY(FunctionExpressions.ASC(var_order))
                .LIMIT(1)
                .build(),
                # This BIND is needed for Apache Jena's SPARQL engine to bind ?licenseLink outside the OPTIONAL. Without
                # the LIMIT clause ?licenseLink seems to become bound even without the BIND (a bug???). Other SPARQL engines
                # don't seem to require this workaround.
                BIND(var_license_link_from_crosslink, _VARIABLES["licenseLink"]),
            ),
            OPTIONAL((var_license, spdx.licenseText, _VARIABLES["licenseDescription"])),
        )
        .build()
    )


def prepare_query_for_count_in_license_search(query: str) -> str:
    var_license = _VARIABLES["license"]
    var_score = Variable("score")

    return (
        QueryBuilder()
        .SELECT(
            count=Aggregates("COUNT", var_license, ["DISTINCT"]),
        )
        .WHERE(*_where_for_text_search(query, var_license, var_score))
        .build()
    )


def search_all_licenses(request: CurationSuggestLicensesRequest) -> CurationSuggestLicensesResult:
    # Simply appending "*" to all queries from users may completely break the Lucene search. For instance the query
    # "CC-BY" would become "CC-BY*", which returns no results for whatever reason.
    # Hyphens are treated as whitespaces by Lucene's StandardAnalyzer (see https://stackoverflow.com/a/10187140), thus
    # "CC-BY" would become "CC BY" (or more precisely "CC OR BY"). Such a text query returns many results (maybe too
    # many?), but the scoring is reasonable to achieve an acceptable user experience.
    query = request.q or "*"

    limit = request.limit
    offset = request.offset

    return CurationSuggestLicensesResult(
        count=count_results_from_license_search(query),
        offset=offset,
        limit=limit,
        results=_search_licenses_and_retrieve_metadata(query, limit, offset),
    )


def _search_licenses_and_retrieve_metadata(
    query: str, limit: int, offset: int
) -> List[CurationSuggestLicensesResultItem]:
    sparql_query = prepare_query_for_license_search_and_metadata_retrieval(query, limit, offset)
    results = query_ontologies_dataset(sparql_query)

    return [_process_result_from_metadata_retrieval(result) for result in results]


def _process_result_from_metadata_retrieval(result) -> CurationSuggestLicensesResultItem:
    result_item = CurationSuggestLicensesResultItem()
    result_item.value = str(result.license)
    result_item.licenseId = str(result.licenseId) if result.licenseId else ""
    result_item.licenseName = str(result.licenseName) if result.licenseName else ""
    result_item.licenseLink = str(result.licenseLink) if result.licenseLink else ""
    result_item.licenseDescription = (
        str(result.licenseDescription) if result.licenseDescription else ""
    )

    return result_item


def count_results_from_license_search(query: str) -> int:
    sparql_query = prepare_query_for_count_in_license_search(query)
    results = query_ontologies_dataset(sparql_query)
    return next(iter(results)).get("count").toPython()


def _get_recommended_licenses(
    request: CurationSuggestLicensesRequest,
) -> CurationSuggestLicensesResult:
    return CurationSuggestLicensesResult(
        count=0, offset=request.offset, limit=request.limit, results=[]
    )


def _get_recently_used_licenses(
    request: CurationSuggestLicensesRequest,
) -> CurationSuggestLicensesResult:
    return CurationSuggestLicensesResult(
        count=0, offset=request.offset, limit=request.limit, results=[]
    )
