from typing import Dict, List

from rdflib import Variable
from rdflib.term import Node

from search.query.items.facets.facet_objects import FacetObject
from search.query.items.search.text_search_query import prepare_where_for_text_search_for_learning_resources
from search.query.utils import query_dalia_dataset
from search.query_builder.query_builder import GROUP, QueryBuilder


def get_existing_facet_items_in_text_search_for_facet(
        text_query: str,
        active_facets: Dict[FacetObject, List[Node]],
        facet: FacetObject
) -> List[Node]:
    sparql_query = prepare_query_for_getting_existing_facet_items_in_text_search_for_facet(
        text_query, active_facets, facet
    )
    results = query_dalia_dataset(sparql_query)
    return process_results_for_getting_existing_facet_items_in_text_search_for_facet(results, facet)


_VARIABLES = {
    "item": Variable("item")
}


def prepare_query_for_getting_existing_facet_items_in_text_search_for_facet(
        text_query: str,
        active_facets: Dict[FacetObject, List[Node]],
        facet: FacetObject
) -> str:
    var_item = _VARIABLES["item"]
    var_lr = Variable("lr")

    return QueryBuilder().SELECT(
        var_item,
        distinct=True
    ).WHERE(
        GROUP(  # This group graph pattern forces the binding of ?lr
            *prepare_where_for_text_search_for_learning_resources(
                text_query,
                active_facets,
                var_lr,
                Variable("score"),
                Variable("created")
            ),
        ),
        # (var_lr, RDF.type, educor.EducationalResource),
        (var_lr, facet.predicate, var_item)
    ).build()
    # TODO: ordering


def process_results_for_getting_existing_facet_items_in_text_search_for_facet(
        results,
        facet: FacetObject
) -> List[Node]:
    return [item for result in results if (item := result.item) in facet.items]
