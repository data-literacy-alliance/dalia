from typing import List, Tuple

from rdflib import Literal, OWL, RDF, SKOS, URIRef, Variable

from search.api_models.api_models import CurationSuggestDisciplinesResultItem, CurationSuggestSearchRequest
from search.query.utils import filter_by_lang, query_ontologies_dataset
from search.query_builder.query_builder import FILTER_EXISTS, QueryBuilder


# Note: This algorithm is quite inefficient and results in a lot of SPARQL queries.
# Another idea would be to pull all disciplines and their narrower/broader nodes at once, e.g. via
#
# PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
# SELECT ?broaderDiscipline ?discipline ?label ?notation
# WHERE {
#   {
#     ?discipline skos:topConceptOf <https://w3id.org/kim/hochschulfaechersystematik/scheme> .
#   }
#   UNION {
#     ?broaderDiscipline skos:narrower ?discipline .
#   }
#   ?discipline a skos:Concept .
#   FILTER NOT EXISTS {
#     ?discipline owl:deprecated true .
#   }
#   ?discipline skos:prefLabel ?label .
#   FILTER(LANG(?label) = "en") .
#   ?discipline skos:notation ?notation .
# }
# ORDER BY ?notation
#
# and then try to construct the object tree.


# data for endpoint /curation/suggest/disciplines
def get_disciplines_suggestions(request: CurationSuggestSearchRequest = None) -> List[CurationSuggestDisciplinesResultItem]:
    all_results = [
        CurationSuggestDisciplinesResultItem(
            value=discipline[0],
            label=discipline[1],
            children=get_child_disciplines_of_discipline(discipline[0])
        ) for discipline in get_top_disciplines()
    ]

    # Apply search filter if provided
    if request and request.q:
        search_term = request.q.lower()
        all_results = [item for item in all_results if search_term in item.label.lower()]

    return all_results


_VARIABLES = {
    "discipline": Variable("discipline"),
    "label": Variable("label"),
    "notation": Variable("notation"),
}


def _prepare_query_to_get_disciplines_metadata(discipline_selection_bgp: Tuple) -> str:
    var_discipline = _VARIABLES["discipline"]
    var_label = _VARIABLES["label"]
    var_notation = _VARIABLES["notation"]

    return QueryBuilder().SELECT(
        var_discipline,
        var_label,
    ).WHERE(
        discipline_selection_bgp,
        (var_discipline, RDF.type, SKOS.Concept),
        FILTER_EXISTS(
            (var_discipline, OWL.deprecated, Literal(True)),
            state=False
        ),
        (var_discipline, SKOS.prefLabel, var_label),
        filter_by_lang(var_label),
        (var_discipline, SKOS.notation, var_notation)
    ).ORDER_BY(
        var_notation
    ).build()


def get_top_disciplines() -> List[Tuple[URIRef, str]]:
    query = prepare_query_to_get_all_top_disciplines()
    results = query_ontologies_dataset(query)
    return _disciplines_data_from_results(results)


def prepare_query_to_get_all_top_disciplines() -> str:
    return _prepare_query_to_get_disciplines_metadata(
        (_VARIABLES["discipline"], SKOS.topConceptOf, URIRef("https://w3id.org/kim/hochschulfaechersystematik/scheme"))
    )


def _disciplines_data_from_results(results) -> List[Tuple[URIRef, str]]:
    return [(result.discipline, str(result.label)) for result in results]


def get_child_disciplines_of_discipline(discipline: URIRef) -> List[CurationSuggestDisciplinesResultItem]:
    query = prepare_query_to_get_all_narrower_disciplines_of_discipline(discipline)
    results = query_ontologies_dataset(query)
    return [
        CurationSuggestDisciplinesResultItem(
            value=discipline[0],
            label=discipline[1],
            children=get_child_disciplines_of_discipline(discipline[0])
        ) for discipline in _disciplines_data_from_results(results)
    ]


def prepare_query_to_get_all_narrower_disciplines_of_discipline(discipline: URIRef) -> str:
    return _prepare_query_to_get_disciplines_metadata(
        (discipline, SKOS.narrower, _VARIABLES["discipline"])
    )
