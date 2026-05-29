from typing import Dict, Iterable

from django.utils.text import slugify
from rdflib import DCTERMS, RDF, URIRef, Variable

from search.api_models.api_models import Community, SocialMedia
from search.query.utils import filter_by_lang, query_dalia_dataset
from search.query_builder.query_builder import OPTIONAL, QueryBuilder, VALUES
from search.rdf.namespace import MoDalia, SCHEMA, wdt


def get_one_to_one_metadata_for_communities(community_uri_refs: Iterable[URIRef]) -> Dict[URIRef, Community]:
    """
    Retrieve the 1-to-1 metadata for each of the given community URIRefs.

    :param community_uri_refs: List of community URIRefs
    :return: Associations between the community URIRefs and their respective metadata.
    """
    if not community_uri_refs:
        return {}

    query = prepare_query_for_one_to_one_metadata_for_communities(community_uri_refs)

    results = query_dalia_dataset(query)
    return {result.community: process_result_for_one_to_one_metadata_for_community(result) for result in results}


def process_result_for_one_to_one_metadata_for_community(result) -> Community:
    community = Community()

    community.id = str(result.community).split("/")[-1]
    community.title = str(result.title)
    community.image = None
    community.url = str(result.url) if result.url else ""
    community.about = str(result.description) if result.description else ""
    community.likes = 0
    community.views = 0
    community.followers = 0
    community.social_media = process_social_media_in_result(result)

    # TODO: could this be moved to the dataclass definition using the @property decorator?
    community.slug = slugify(community.title)

    return community


def process_social_media_in_result(result):
    social_media = []

    if result.zenodo_community_id:
        social_media.append(
            SocialMedia(name="Zenodo", url="https://zenodo.org/communities/" + str(result.zenodo_community_id))
        )
    if result.youtube_channel_id:
        social_media.append(
            SocialMedia(name="YouTube", url="https://www.youtube.com/channel/" + str(result.youtube_channel_id))
        )
    if result.bluesky_handle:
        social_media.append(
            SocialMedia(name="Bluesky", url="https://bsky.app/profile/" + str(result.bluesky_handle))
        )
    if result.mastodon_address:
        server = str(result.mastodon_address).split("@")[-1]
        handle = str(result.mastodon_address).split("@")[0]
        social_media.append(
            SocialMedia(name="Mastodon", url=f"https://{server}/@{handle}")
        )
    if result.linkedin_id:
        social_media.append(
            SocialMedia(name="LinkedIn", url="https://www.linkedin.com/company/" + str(result.linkedin_id))
        )

    return social_media


_VARIABLES = {
    "community": Variable("community"),
    "description": Variable("description"),
    "title": Variable("title"),
    "bluesky_handle": Variable("bluesky_handle"),
    "youtube_channel_id": Variable("youtube_channel_id"),
    "mastodon_address": Variable("mastodon_address"),
    "linkedin_id": Variable("linkedin_id"),
    "zenodo_community_id": Variable("zenodo_community_id"),
    "url": Variable("url"),
}


def prepare_query_for_one_to_one_metadata_for_communities(community_uri_refs: Iterable[URIRef]) -> str:
    resource_uri_ref_blocks = [[uri_ref] for uri_ref in community_uri_refs]

    var_community = _VARIABLES["community"]
    var_description = _VARIABLES["description"]

    return QueryBuilder().SELECT(
        *_VARIABLES.values()
    ).WHERE(
        VALUES(
            [var_community],
            resource_uri_ref_blocks
        ),
        (var_community, RDF.type, MoDalia.Community),
        OPTIONAL(
            (var_community, DCTERMS.description, var_description),
            filter_by_lang(var_description),
        ),
        OPTIONAL((var_community, DCTERMS.title, _VARIABLES["title"])),
        OPTIONAL((var_community, wdt.Bluesky_handle, _VARIABLES["bluesky_handle"])),
        OPTIONAL((var_community, wdt.YouTube_channel_ID, _VARIABLES["youtube_channel_id"])),
        OPTIONAL((var_community, wdt.Mastodon_address, _VARIABLES["mastodon_address"])),
        OPTIONAL((var_community, wdt.LinkedIn_company_or_organization_ID, _VARIABLES["linkedin_id"])),
        OPTIONAL((var_community, wdt.Zenodo_communities_ID, _VARIABLES["zenodo_community_id"])),
        OPTIONAL((var_community, SCHEMA.url, _VARIABLES["url"])),
    ).build()
