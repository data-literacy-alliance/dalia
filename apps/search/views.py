"""
REST API views for search and metadata retrieval endpoints.

These views provide public access to:
- Basic search filters (vocabularies)
- Learning resource metadata (individual items)
- Full-text search with facets
- Community metadata
- Community items
"""

from uuid import UUID

from django.http import HttpResponse, HttpResponseNotFound
from django.utils.text import slugify
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from curation.models.communities import Community as PgCommunity
from search import serializers
from search.api_models.api_models import Community as ApiCommunity
from search.api_models.api_models import SocialMedia as ApiSocialMedia
from rdflib import URIRef
from search.query.communities.communities import get_metadata_for_community
from search.query.communities.one_to_one_metadata import get_one_to_one_metadata_for_communities
from search.query.communities.community_items import get_items_for_community
from search.suggest.communities import get_communities_suggestions
from search.query.items.basic_search_filters.basic_search_filters import get_basic_search_filters
from search.query.items.metadata.items import get_metadata_for_learning_resource
from search.query.items.search.comprehensive_search import search_items_comprehensive
from search.query.items.search.sources import get_enabled_search_sources
from search.query.items.search.producers.postgres_producer import postgres_hydrate


class BasicSearchFiltersView(APIView):
    """
    GET /v1/basic-search-filters/

    Returns available filter options for search (vocabularies).
    Public endpoint - no authentication required.
    """

    permission_classes = [AllowAny]

    def get(self, request: Request) -> HttpResponse:
        serializer = serializers.BasicSearchFilterSerializer(get_basic_search_filters(), many=True)
        return Response(serializer.data)


class ItemView(APIView):
    """
    GET /v1/items/<uuid:resource_id>/

    Returns metadata for a single learning resource.
    Public endpoint - no authentication required.
    """

    permission_classes = [AllowAny]

    def get(self, request: Request, resource_id: UUID) -> HttpResponse:
        item = get_metadata_for_learning_resource(resource_id)

        if not item and "postgres" in get_enabled_search_sources():
            # Fuseki has no record for this UUID; try the postgres producer.
            pg_results = postgres_hydrate([str(resource_id)])
            item = pg_results[0] if pg_results else None

        if not item:
            return HttpResponseNotFound()

        serializer = serializers.ItemSerializer(item)
        return Response(serializer.data)


class ItemSearchView(APIView):
    """
    POST /v1/items/

    Search learning resources with filters and facets.
    Request body: ItemSearchRequest (query, facets, offset, limit)
    Response: ItemSearchResult (count, results, facets)
    Public endpoint - no authentication required.
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> HttpResponse:
        request_serializer = serializers.ItemSearchRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        search_result = search_items_comprehensive(request_serializer.validated_data)

        result_serializer = serializers.ItemSearchResultSerializer(search_result)
        return Response(result_serializer.data)


class CurationSuggestCommunitiesView(APIView):
    """GET /v1/curation/suggest/communities/ -- community autocomplete"""

    permission_classes = [AllowAny]

    def get(self, request: Request) -> HttpResponse:
        request_serializer = serializers.CurationSuggestSearchRequestSerializer(
            data=request.query_params
        )
        request_serializer.is_valid(raise_exception=True)
        result_serializer = serializers.CurationSuggestPaginatedResultSerializer(
            get_communities_suggestions(request_serializer.validated_data)
        )
        return Response(result_serializer.data)


class CommunityView(APIView):
    """
    GET /v1/communities/<uuid:community_id>/

    Returns metadata for a community.
    Public endpoint - no authentication required.
    """

    permission_classes = [AllowAny]

    def get(self, request: Request, community_id: UUID) -> HttpResponse:
        fuseki_uri = f'https://id.dalia.education/community/{community_id}'

        # PostgreSQL wins — look up by Fuseki URI first, then by PG UUID (PG-only communities)
        pg = (
            PgCommunity.objects.filter(uri=fuseki_uri).first()
            or PgCommunity.objects.filter(uuid=community_id).first()
        )

        if pg:
            social_media_links = list(pg.social_media_links.all())
            # TODO: remove Fuseki gap-filling once all communities are fully replicated in PostgreSQL
            needs_fuseki = not pg.description or not pg.website_url or not pg.image or not social_media_links
            fuseki_data = None
            if needs_fuseki:
                try:
                    uri_ref = URIRef(fuseki_uri)
                    meta = get_one_to_one_metadata_for_communities([uri_ref])
                    fuseki_data = meta.get(uri_ref)
                except Exception:
                    pass

            community = ApiCommunity(
                id=str(community_id),
                slug=pg.slug or slugify(pg.title),
                title=pg.title,
                image=pg.image or (fuseki_data.image if fuseki_data else None),
                url=pg.website_url or (fuseki_data.url if fuseki_data else '') or '',
                about=pg.description or (fuseki_data.about if fuseki_data else '') or '',
                likes=0,
                views=0,
                followers=0,
                social_media=(
                    [ApiSocialMedia(name=sm.name, url=sm.url) for sm in social_media_links]
                    if social_media_links
                    else [ApiSocialMedia(name=sm.name, url=sm.url) for sm in (fuseki_data.social_media or [])]
                    if fuseki_data
                    else []
                ),
            )
        else:
            # Not in PG yet — fall back to Fuseki directly
            community = get_metadata_for_community(community_id)

        if not community:
            return HttpResponseNotFound()

        serializer = serializers.CommunitySerializer(community)
        return Response(serializer.data)


class CommunityItemsView(APIView):
    """
    GET /v1/communities/<uuid:community_id>/items/

    Returns all learning resources in a community.
    Public endpoint - no authentication required.
    """

    permission_classes = [AllowAny]

    def get(self, request: Request, community_id: UUID) -> HttpResponse:
        items = get_items_for_community(community_id)

        if items is None:
            return HttpResponseNotFound()

        serializer = serializers.ItemSerializer(items, many=True)
        return Response(serializer.data)
