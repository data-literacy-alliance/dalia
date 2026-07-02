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
from rest_framework.authentication import SessionAuthentication

from curation.models.communities import Community as PgCommunity
from search import serializers
from search.api_models.api_models import Community as ApiCommunity
from search.api_models.api_models import SocialMedia as ApiSocialMedia
from rdflib import URIRef
from search.query.communities.communities import get_metadata_for_community
from search.query.communities.one_to_one_metadata import get_one_to_one_metadata_for_communities
from search.query.communities.community_items import (
    get_items_for_community,
    get_resources_for_community,
)
from search.suggest.communities import get_communities_suggestions
from search.query.items.basic_search_filters.basic_search_filters import get_basic_search_filters
from search.query.items.metadata.items import (
    get_metadata_for_learning_resource,
    get_metadata_for_learning_resources,
)
from search.query.items.search.comprehensive_search import search_items_comprehensive
from search.query.items.search.sources import get_enabled_search_sources
from search.query.items.search.producers.postgres_producer import postgres_hydrate
from curation.models import ResourceContent, ViewEvent
from curation.services import log_view_event


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

        item.views = ViewEvent.objects.filter(resource_uuid=resource_id).count()

        serializer = serializers.ItemSerializer(item)
        return Response(serializer.data)


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        pass  # view tracking is low-risk; skip CSRF for this endpoint only


class ItemViewEventView(APIView):
    """
    POST /v1/items/<uuid:resource_id>/view/

    Records a view event for a learning resource.
    Called client-side from the browser so that real user/session cookies are available.
    Deduplicates per authenticated user or anonymous session within a 24-hour window.
    """

    permission_classes = [AllowAny]
    authentication_classes = [CsrfExemptSessionAuthentication]

    def post(self, request: Request, resource_id: UUID) -> HttpResponse:
        from django.utils import timezone
        from datetime import timedelta

        user = request.user if request.user.is_authenticated else None
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key or ""

        cutoff = timezone.now() - timedelta(hours=24)
        already_viewed = False
        if user:
            already_viewed = ViewEvent.objects.filter(
                resource_uuid=resource_id, user=user, created__gte=cutoff
            ).exists()
        elif session_key:
            already_viewed = ViewEvent.objects.filter(
                resource_uuid=resource_id, session_id=session_key, created__gte=cutoff
            ).exists()

        if not already_viewed:
            content_object = None
            try:
                content_object = ResourceContent.objects.get(
                    resource__uuid=resource_id, is_active=True
                )
            except ResourceContent.DoesNotExist:
                pass

            log_view_event(
                user=user,
                content_object=content_object,
                resource_uuid=resource_id,
                session_id=session_key,
                ip_address=request.META.get("REMOTE_ADDR", ""),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
            return Response(status=201)

        return Response(status=204)


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
        fuseki_uri = f"https://id.dalia.education/community/{community_id}"

        # PostgreSQL wins — look up by Fuseki URI first, then by PG UUID (PG-only communities)
        pg = (
            PgCommunity.objects.filter(uri=fuseki_uri).first()
            or PgCommunity.objects.filter(uuid=community_id).first()
        )

        if pg:
            social_media_links = list(pg.social_media_links.all())
            # TODO: remove Fuseki gap-filling once all communities are fully replicated in PostgreSQL
            needs_fuseki = (
                not pg.description or not pg.website_url or not pg.image or not social_media_links
            )
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
                url=pg.website_url or (fuseki_data.url if fuseki_data else "") or "",
                about=pg.description or (fuseki_data.about if fuseki_data else "") or "",
                likes=0,
                views=0,
                followers=0,
                social_media=(
                    [ApiSocialMedia(name=sm.name, url=sm.url) for sm in social_media_links]
                    if social_media_links
                    else [
                        ApiSocialMedia(name=sm.name, url=sm.url)
                        for sm in (fuseki_data.social_media or [])
                    ]
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
        fuseki_uri = f"https://id.dalia.education/community/{community_id}"

        # PG is the primary source of truth — look up by Fuseki URI first, then by PG UUID.
        pg = (
            PgCommunity.objects.filter(uri=fuseki_uri).first()
            or PgCommunity.objects.filter(uuid=community_id).first()
        )

        if pg:
            # Primary path: PG is the source of truth for community resources.
            resource_uuids = list(
                pg.resource_relations.filter(
                    content__is_active=True,
                    content__resource__is_published=True,
                    content__resource__is_removed=False,
                )
                .values_list("content__resource__uuid", flat=True)
                .distinct()
            )

            if resource_uuids:
                items = postgres_hydrate([str(u) for u in resource_uuids])
                serializer = serializers.ItemSerializer(items, many=True)
                return Response(serializer.data)

            # TODO: Remove this Fuseki fallback once PG is the sole database for resource content.
            # For now, also check Fuseki for resources linked to this community's URI.
            if pg.uri:
                fuseki_resource_uri_refs = get_resources_for_community(URIRef(pg.uri))
                if fuseki_resource_uri_refs:
                    fuseki_items = get_metadata_for_learning_resources(fuseki_resource_uri_refs)
                    if fuseki_items:
                        serializer = serializers.ItemSerializer(fuseki_items, many=True)
                        return Response(serializer.data)

            # Community exists but has no linked resources in either PG or Fuseki.
            return Response([])

        # Community not found in PG — fall back to Fuseki-only path for legacy data.
        items = get_items_for_community(community_id)
        if items is None:
            return HttpResponseNotFound()

        serializer = serializers.ItemSerializer(items, many=True)
        return Response(serializer.data)
