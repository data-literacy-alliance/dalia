from typing import Dict, List

from rdflib import Variable
from rdflib.term import Node

from search.query.items.facets.facet_objects import FacetObject
from search.query.items.search.text_search_query import (
    prepare_where_for_text_search_for_learning_resources,
)
from search.query.utils import query_dalia_dataset
from search.query_builder.query_builder import Aggregates, QueryBuilder


def count_results(text_query: str, active_facets: Dict[FacetObject, List[Node]]) -> int:
    sparql_query = prepare_query_for_count_in_text_search(text_query, active_facets)
    results = query_dalia_dataset(sparql_query)
    return next(iter(results)).get("count").toPython()


def prepare_query_for_count_in_text_search(
    text_query: str, active_facets: Dict[FacetObject, List[Node]]
) -> str:
    var_lr = Variable("lr")
    var_score = Variable("score")
    var_created = Variable("created")

    return (
        QueryBuilder()
        .SELECT(
            count=Aggregates("COUNT", var_lr, ["DISTINCT"]),
        )
        .WHERE(
            *prepare_where_for_text_search_for_learning_resources(
                text_query, active_facets, var_lr, var_score, var_created
            )
        )
        .build()
    )
