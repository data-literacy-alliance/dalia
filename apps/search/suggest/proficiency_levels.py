from typing import List

from rdflib import RDF, RDFS, Variable

from search.api_models.api_models import CurationSuggestSearchRequest, LabelValueItem
from search.query.utils import filter_by_lang, query_ontologies_dataset
from search.query_builder.query_builder import QueryBuilder
from search.rdf.namespace import MoDalia


# data for endpoint /curation/suggest/proficiency-levels
def get_proficiency_levels_suggestions(
    request: CurationSuggestSearchRequest = None,
) -> List[LabelValueItem]:
    query = prepare_query_to_get_proficiency_levels()
    results = query_ontologies_dataset(query)
    all_results = [_process_result(result) for result in results]

    # Apply search filter if provided
    if request and request.q:
        search_term = request.q.lower()
        all_results = [item for item in all_results if search_term in item.label.lower()]

    return all_results


_VARIABLES = {
    "level": Variable("level"),
    "label": Variable("label"),
}


def prepare_query_to_get_proficiency_levels() -> str:
    var_level = _VARIABLES["level"]
    var_level_order = Variable("levelOrder")
    var_label = _VARIABLES["label"]

    return (
        QueryBuilder()
        .SELECT(*_VARIABLES.values())
        .WHERE(
            (var_level, RDF.type, MoDalia.Proficiency),
            (var_level, MoDalia.hasOrder, var_level_order),
            (var_level, RDFS.label, var_label),
            filter_by_lang(var_label),
        )
        .ORDER_BY(var_level_order)
        .build()
    )


def _process_result(result) -> LabelValueItem:
    return LabelValueItem(label=str(result.label), value=str(result.level))
