from collections import defaultdict
from typing import Dict, List, Set

from rdflib import DCTERMS, RDF, URIRef, Variable

from search.api_models.api_models import Community
from search.query.communities.one_to_one_metadata import get_one_to_one_metadata_for_communities
from search.query.utils import query_dalia_dataset
from search.query_builder.query_builder import GROUP, QueryBuilder, UNION, VALUES
from search.rdf.namespace import MoDalia, bibframe_lite_relation, educor, rec

_VARIABLES = {"lr": Variable("lr"), "community": Variable("community")}


def prepare_query_for_learning_resource_to_communities_associations(
    resource_uri_refs: List[URIRef],
) -> str:
    var_lr = _VARIABLES["lr"]
    var_community = _VARIABLES["community"]
    var_community_title = Variable("community_title")

    resource_uri_ref_blocks = [[uri_ref] for uri_ref in resource_uri_refs]

    return (
        QueryBuilder()
        .SELECT(*_VARIABLES.values())
        .WHERE(
            VALUES([var_lr], resource_uri_ref_blocks),
            (var_lr, RDF.type, educor.EducationalResource),
            # This GROUP-UNION pattern is equivalent to "?lr rec:recommender|bflr:supportinghost ?community"
            # (AlternativePath expression in SPARQL).
            GROUP(
                (var_lr, rec.recommender, var_community),
            ),
            UNION(
                (var_lr, bibframe_lite_relation.supportinghost, var_community),
            ),
            (var_community, RDF.type, MoDalia.Community),
            (var_community, DCTERMS.title, var_community_title),
        )
        .GROUP_BY(  # prevents duplicates in case the same community is both rec:recommender and bflr:supportinghost
            var_lr, var_community
        )
        .ORDER_BY(var_community_title)
        .build()
    )


def process_results_for_learning_resource_to_communities_associations(
    results,
) -> Dict[URIRef, List[URIRef]]:
    lr_communities = defaultdict(list)

    for result in results:
        lr_communities[result.lr].append(result.community)

    return lr_communities


def get_learning_resource_to_communities_associations(
    resource_uri_refs: List[URIRef],
) -> Dict[URIRef, List[URIRef]]:
    query = prepare_query_for_learning_resource_to_communities_associations(resource_uri_refs)
    results = query_dalia_dataset(query)
    return process_results_for_learning_resource_to_communities_associations(results)


def get_communities_for_resources(resource_uri_refs: List[URIRef]) -> Dict[URIRef, List[Community]]:
    """
    Retrieve the community metadata for each of the given learning resource URIRefs.

    :param resource_uri_refs: List of learning resource URIRefs
    :return: Associations between the learning resource URIRefs and their respective list of communities (ordered by
        community title).
    """
    lr_to_communities_uri_refs_associations = get_learning_resource_to_communities_associations(
        resource_uri_refs
    )

    # the set removes any duplicates
    all_community_uri_refs: Set[URIRef] = {
        community_uri_ref
        for communities_list in lr_to_communities_uri_refs_associations.values()
        for community_uri_ref in communities_list
    }

    communities_metadata = get_one_to_one_metadata_for_communities(all_community_uri_refs)

    # lr_to_communities_associations = {}
    # for lr_uri_ref, community_uri_refs in lr_to_communities_uri_refs_associations.items():
    #     communities_for_lr = []
    #     for community_uri_ref in community_uri_refs:
    #         communities_for_lr.append(communities_metadata[community_uri_ref])
    #
    #     lr_to_communities_associations[lr_uri_ref] = communities_for_lr
    # return lr_to_communities_associations

    # equivalent to the explicit for loop
    return {
        lr_uri_ref: list(
            map(
                lambda community_uri_ref: communities_metadata[community_uri_ref],
                community_uri_refs,
            )
        )
        for lr_uri_ref, community_uri_refs in lr_to_communities_uri_refs_associations.items()
    }
