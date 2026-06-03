from typing import List

from rdflib import RDFS, SKOS, Variable

from search.api_models.api_models import CurationSuggestSearchRequest, LabelValueItem
from search.query.utils import filter_by_lang, query_ontologies_dataset
from search.query_builder.query_builder import FILTER, GROUP, Operators, QueryBuilder, UNION
from search.rdf.namespace import MoDalia, hcrt


# data for endpoint /curation/suggest/learning-resource-types
def get_learning_resource_types_suggestions(
    request: CurationSuggestSearchRequest = None,
) -> List[LabelValueItem]:
    query = prepare_query_to_get_learning_resource_types()
    results = query_ontologies_dataset(query)
    all_results = [_process_result(result) for result in results]

    # Apply search filter if provided
    if request and request.q:
        search_term = request.q.lower()
        all_results = [item for item in all_results if search_term in item.label.lower()]

    return all_results


_VARIABLES = {
    "lrt": Variable("lrt"),
    "label": Variable("label"),
}

_EXCLUDED_LEARNING_RESOURCE_TYPES = [
    # media type exceptions
    hcrt.audio,
    hcrt.image,
    hcrt.slide,
    hcrt.text,
    hcrt.video,
    # duplicate definitions - we prefer the items defined via MoDalia
    hcrt.questionnaire,
    hcrt.web_page,
]


def prepare_query_to_get_learning_resource_types() -> str:
    var_lrt = _VARIABLES["lrt"]
    var_label = _VARIABLES["label"]

    return (
        QueryBuilder()
        .SELECT(*_VARIABLES.values())
        .WHERE(
            QueryBuilder()
            .SELECT(var_lrt, distinct=True)
            .WHERE(
                GROUP(
                    (var_lrt, RDFS.subClassOf, MoDalia.LearningResourceType),
                ),
                UNION(
                    (var_lrt, SKOS.topConceptOf, hcrt.scheme),
                ),
                FILTER(Operators.IN(var_lrt, *_EXCLUDED_LEARNING_RESOURCE_TYPES, state=False)),
            )
            .build(),
            (var_lrt, SKOS.prefLabel, var_label),
            filter_by_lang(var_label),
        )
        .ORDER_BY(var_label)
        .build()
    )


def _process_result(result) -> LabelValueItem:
    return LabelValueItem(label=str(result.label), value=str(result.lrt))
