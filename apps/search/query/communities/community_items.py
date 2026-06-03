from typing import List, Optional
from uuid import UUID

from rdflib import RDF, URIRef, Variable

from search.api_models.api_models import Item
from search.query.communities.communities import get_metadata_for_communities
from search.query.items.metadata.items import get_metadata_for_learning_resources
from search.query.utils import query_dalia_dataset
from search.query_builder.query_builder import GROUP, QueryBuilder, UNION, VALUES
from search.rdf.dalia_kb import community_uri_ref
from search.rdf.namespace import MoDalia, bibframe_lite_relation, educor, rec


# data for endpoint /communities/{communityId}/items
def get_items_for_community(community_id: UUID) -> Optional[List[Item]]:
    _community_uri_ref = community_uri_ref(community_id)

    # TODO: parallelize these calls
    # TODO: This could be a simple ASK query
    communities = get_metadata_for_communities([_community_uri_ref])
    if not communities:
        # indicate 404
        return None

    resource_uri_refs = get_resources_for_community(_community_uri_ref)
    resources = get_metadata_for_learning_resources(resource_uri_refs)

    # indicate 200
    return resources


def get_resources_for_community(community_uri_ref: URIRef) -> List[URIRef]:
    query = prepare_query_for_resources_of_community(community_uri_ref)
    results = query_dalia_dataset(query)
    return [process_result_for_resources_of_community(result) for result in results]


def process_result_for_resources_of_community(result) -> URIRef:
    return result.lr


_VARIABLES = {"lr": Variable("lr")}


def prepare_query_for_resources_of_community(community_uri_ref: URIRef) -> str:
    var_lr = _VARIABLES["lr"]
    var_community = Variable("community")

    return (
        QueryBuilder()
        .SELECT(
            var_lr,
            distinct=True,  # prevents duplicates in case the same community is both rec:recommender and bflr:supportinghost
        )
        .WHERE(
            VALUES([var_community], [[community_uri_ref]]),
            (var_community, RDF.type, MoDalia.Community),
            # This GROUP-UNION pattern is equivalent to "?lr rec:recommender|bflr:supportinghost ?community"
            # (AlternativePath expression in SPARQL).
            GROUP(
                (var_lr, rec.recommender, var_community),
            ),
            UNION(
                (var_lr, bibframe_lite_relation.supportinghost, var_community),
            ),
            (var_lr, RDF.type, educor.EducationalResource),
        )
        .build()
    )
