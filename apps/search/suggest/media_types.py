from typing import List

from rdflib import RDFS, SKOS, Variable

from search.api_models.api_models import CurationSuggestSearchRequest, LabelValueItem
from search.query.utils import filter_by_lang, query_ontologies_dataset
from search.query_builder.query_builder import QueryBuilder
from search.rdf.namespace import MoDalia


# data for endpoint /curation/suggest/media-types
def get_media_types_suggestions(request: CurationSuggestSearchRequest = None) -> List[LabelValueItem]:
    query = prepare_query_to_get_media_types()
    results = query_ontologies_dataset(query)
    all_results = [_process_result(result) for result in results]

    # Apply search filter if provided
    if request and request.q:
        search_term = request.q.lower()
        all_results = [item for item in all_results if search_term in item.label.lower()]

    return all_results


_VARIABLES = {
    "type": Variable("type"),
    "label": Variable("label"),
}


def prepare_query_to_get_media_types() -> str:
    var_type = _VARIABLES["type"]
    var_label = _VARIABLES["label"]

    return QueryBuilder().SELECT(
        *_VARIABLES.values()
    ).WHERE(
        (var_type, RDFS.subClassOf, MoDalia.MediaType),
        (var_type, SKOS.prefLabel, var_label),
        filter_by_lang(var_label),
    ).ORDER_BY(
        var_label
    ).build()


def _process_result(result) -> LabelValueItem:
    return LabelValueItem(
        label=str(result.label),
        value=str(result.type)
    )
