from typing import List, Optional
from uuid import UUID

from rdflib import URIRef

from search.api_models.api_models import Community
from search.query.communities.one_to_one_metadata import get_one_to_one_metadata_for_communities
from search.rdf.dalia_kb import community_uri_ref


# data for endpoint /communities/{communityId}
def get_metadata_for_community(community_id: UUID) -> Optional[Community]:
    communities = get_metadata_for_communities([community_uri_ref(community_id)])

    if not communities:
        # indicate 404
        return None

    # indicate 200
    return communities[0]


def get_metadata_for_communities(community_uri_refs: List[URIRef]) -> List[Community]:
    communities_metadata = get_one_to_one_metadata_for_communities(community_uri_refs)

    return [
        community
        for community_uri_ref in community_uri_refs
        if (community := communities_metadata.get(community_uri_ref))
    ]
