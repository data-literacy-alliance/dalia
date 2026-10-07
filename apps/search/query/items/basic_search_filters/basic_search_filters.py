from typing import List

from rdflib import RDF, Variable

from search.api_models.api_models import (
    BasicSearchFilter,
    BasicSearchFilterKey,
    BasicSearchFilterValue,
)
from curation.models.communities import Community as CommunityModel
from search.query.items.facets.facet_objects import COMMUNITY_FACET, FacetObject
from search.query.items.search.text_search import _ITEM_SEARCH_FACETS
from search.query.utils import query_dalia_dataset
from search.query_builder.query_builder import GROUP, QueryBuilder, UNION
from search.rdf.namespace import bibframe_lite_relation, educor, rec

# Reuse the same facets as the search results page (avoids duplication)
_BASIC_SEARCH_FILTER_FACETS = _ITEM_SEARCH_FACETS


# data for endpoint /basic-search-filters
def get_basic_search_filters() -> List[BasicSearchFilter]:
    # TODO: These calls could be parallelized, because they end up in blocking SPARQL queries
    return [get_basic_search_filters_for_facet(facet) for facet in _BASIC_SEARCH_FILTER_FACETS]


def get_basic_search_filters_for_facet(facet: FacetObject) -> BasicSearchFilter:
    # TODO: What happens in the UI if there is no item?
    return BasicSearchFilter(
        key=BasicSearchFilterKey(name=facet.key, label=facet.label),
        values=get_all_existing_filter_items_for_facet(facet),
    )


def get_all_existing_filter_items_for_facet(facet: FacetObject) -> List[BasicSearchFilterValue]:
    if facet is COMMUNITY_FACET:
        # Use PostgreSQL as the authoritative community source — covers all active communities
        # (not just the 37 in the hardcoded COMMUNITY_FACET.items dict).
        communities = CommunityModel.objects.filter(is_active=True).order_by("title")
        return [
            BasicSearchFilterValue(
                label=c.title,
                value=c.uri or f"https://id.dalia.education/community/{c.uuid}",
            )
            for c in communities
        ]

    query = prepare_query_to_get_all_existing_filter_items_for_facet(facet)

    query_results = query_dalia_dataset(query)

    existing_filter_items_from_database = [result.item for result in query_results]

    # This ensures the list order is according to the order of the dictionary facet.items.
    return [
        BasicSearchFilterValue(label=item_label, value=str(item_key))
        for item_key, item_label in facet.items.items()
        if item_key in existing_filter_items_from_database
    ]


_VARIABLES = {"item": Variable("item")}


def prepare_query_to_get_all_existing_filter_items_for_facet(facet: FacetObject) -> str:
    var_item = _VARIABLES["item"]
    var_lr = Variable("lr")

    if facet is COMMUNITY_FACET:
        # hasCommunity predicate does not exist in Fuseki; community membership
        # is expressed via rec:recommender (or bflr:supportinghost for future data).
        return (
            QueryBuilder()
            .SELECT(var_item, distinct=True)
            .WHERE(
                (var_lr, RDF.type, educor.EducationalResource),
                GROUP((var_lr, rec.recommender, var_item)),
                UNION((var_lr, bibframe_lite_relation.supportinghost, var_item)),
            )
            .build()
        )

    return (
        QueryBuilder()
        .SELECT(var_item, distinct=True)
        .WHERE((var_lr, RDF.type, educor.EducationalResource), (var_lr, facet.predicate, var_item))
        .build()
    )
