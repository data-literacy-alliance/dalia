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
from rest_framework.permissions import AllowAny, IsAuthenticated
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
from search.rdf.dalia_kb import lr_uri_ref
from search.query.items.search.comprehensive_search import search_items_comprehensive
from search.query.items.search.sources import get_enabled_search_sources
from search.query.items.search.producers.postgres_producer import postgres_hydrate
from curation.models import ResourceContent, ViewEvent
from curation.models import Bookmark as BookmarkModel, Like as LikeModel
from curation.services import log_view_event, toggle_bookmark_for_resource, toggle_like_for_resource
from django.contrib.contenttypes.models import ContentType

PAGE_SIZE = 9


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

        # Real likes count (resource_uuid-based + legacy GFK-only rows)
        rc_for_likes = ResourceContent.objects.filter(
            resource__uuid=resource_id, is_active=True
        ).first()
        ct_rc = ContentType.objects.get_for_model(ResourceContent)
        item.likes = LikeModel.objects.filter(resource_uuid=resource_id).count()
        if rc_for_likes:
            item.likes += LikeModel.objects.filter(
                content_type=ct_rc, object_id=rc_for_likes.pk, resource_uuid__isnull=True
            ).count()

        # is_bookmarked / is_liked for authenticated users
        if request.user.is_authenticated:
            item.is_bookmarked = BookmarkModel.objects.filter(
                user=request.user, resource_uuid=resource_id
            ).exists()
            item.is_liked = LikeModel.objects.filter(
                user=request.user, resource_uuid=resource_id
            ).exists()
            if rc_for_likes and not item.is_bookmarked:
                item.is_bookmarked = BookmarkModel.objects.filter(
                    user=request.user, content_type=ct_rc, object_id=rc_for_likes.pk
                ).exists()
            if rc_for_likes and not item.is_liked:
                item.is_liked = LikeModel.objects.filter(
                    user=request.user, content_type=ct_rc, object_id=rc_for_likes.pk
                ).exists()

        serializer = serializers.ItemSerializer(item)
        return Response(serializer.data)


class ItemBookmarkView(APIView):
    """
    POST /v1/items/<uuid:resource_id>/bookmark/

    Toggle bookmark for a learning resource. Authentication required.
    Returns 201 + {"bookmarked": true} when added, 200 + {"bookmarked": false} when removed.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, resource_id: UUID) -> HttpResponse:
        active, _ = toggle_bookmark_for_resource(request.user, resource_id)
        if active:
            return Response({"bookmarked": True}, status=201)
        return Response({"bookmarked": False}, status=200)


class ItemLikeView(APIView):
    """
    POST /v1/items/<uuid:resource_id>/like/

    Toggle like for a learning resource. Authentication required.
    Returns 201 + {"liked": true} when added, 200 + {"liked": false} when removed.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, resource_id: UUID) -> HttpResponse:
        active, _ = toggle_like_for_resource(request.user, resource_id)
        if active:
            return Response({"liked": True}, status=201)
        return Response({"liked": False}, status=200)


class ItemInteractionsView(APIView):
    """
    GET /v1/items/<uuid:resource_id>/interactions/

    Returns interaction state (bookmarked, liked, likes count) for the current user.
    Authentication required.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, resource_id: UUID) -> HttpResponse:
        ct = ContentType.objects.get_for_model(ResourceContent)
        rc = ResourceContent.objects.filter(resource__uuid=resource_id, is_active=True).first()

        # Likes count: resource_uuid-based (all new records) + legacy GFK-only rows
        likes_count = LikeModel.objects.filter(resource_uuid=resource_id).count()
        if rc:
            likes_count += LikeModel.objects.filter(
                content_type=ct, object_id=rc.pk, resource_uuid__isnull=True
            ).count()

        is_bookmarked = BookmarkModel.objects.filter(
            user=request.user, resource_uuid=resource_id
        ).exists()
        if not is_bookmarked and rc:
            is_bookmarked = BookmarkModel.objects.filter(
                user=request.user, content_type=ct, object_id=rc.pk
            ).exists()

        is_liked = LikeModel.objects.filter(user=request.user, resource_uuid=resource_id).exists()
        if not is_liked and rc:
            is_liked = LikeModel.objects.filter(
                user=request.user, content_type=ct, object_id=rc.pk
            ).exists()

        return Response(
            {
                "is_bookmarked": is_bookmarked,
                "is_liked": is_liked,
                "likes": likes_count,
            }
        )


class UserBookmarksListView(APIView):
    """
    GET /v1/activities/bookmarks/?page=N

    Returns paginated list of bookmarked resources for the current user.
    Authentication required.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> HttpResponse:
        page = max(1, int(request.query_params.get("page", 1)))
        qs = BookmarkModel.objects.filter(user=request.user).order_by("-created")
        total = qs.count()
        qs_page = list(qs[(page - 1) * PAGE_SIZE : page * PAGE_SIZE])

        pg_bookmarks = []
        fuseki_uuids = []
        for bm in qs_page:
            if bm.content_type_id is not None:
                pg_bookmarks.append(bm)
            elif bm.resource_uuid:
                fuseki_uuids.append(str(bm.resource_uuid))

        # Collect PG resource UUIDs for hydration
        pg_uuids = []
        for bm in pg_bookmarks:
            if bm.resource_uuid:
                pg_uuids.append(str(bm.resource_uuid))
            else:
                # Legacy row without resource_uuid — resolve via ResourceContent
                rc = ResourceContent.objects.filter(pk=bm.object_id).first()
                if rc:
                    pg_uuids.append(str(rc.resource.uuid))

        pg_items = postgres_hydrate(pg_uuids) if pg_uuids else []

        fuseki_items = []
        if fuseki_uuids:
            try:
                fuseki_items = (
                    get_metadata_for_learning_resources([lr_uri_ref(u) for u in fuseki_uuids]) or []
                )
            except Exception:
                pass

        # Merge preserving bookmark order from qs_page
        pg_by_uuid = {str(i.id): i for i in pg_items}
        fuseki_by_uuid = {str(i.id): i for i in fuseki_items}
        ordered_items = []
        for bm in qs_page:
            uuid_str = str(bm.resource_uuid) if bm.resource_uuid else None
            if not uuid_str and bm.content_type_id is not None:
                rc = ResourceContent.objects.filter(pk=bm.object_id).first()
                if rc:
                    uuid_str = str(rc.resource.uuid)
            if uuid_str:
                item = pg_by_uuid.get(uuid_str) or fuseki_by_uuid.get(uuid_str)
                if item:
                    ordered_items.append(item)

        serializer = serializers.ItemSerializer(ordered_items, many=True)
        has_next = (page * PAGE_SIZE) < total
        has_prev = page > 1
        return Response(
            {
                "count": total,
                "next": f"?page={page + 1}" if has_next else None,
                "previous": f"?page={page - 1}" if has_prev else None,
                "results": serializer.data,
            }
        )


class UserLikesListView(APIView):
    """
    GET /v1/activities/likes/?page=N

    Returns paginated list of liked resources for the current user.
    Authentication required.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> HttpResponse:
        page = max(1, int(request.query_params.get("page", 1)))
        qs = LikeModel.objects.filter(user=request.user).order_by("-created")
        total = qs.count()
        qs_page = list(qs[(page - 1) * PAGE_SIZE : page * PAGE_SIZE])

        pg_likes = []
        fuseki_uuids = []
        for lk in qs_page:
            if lk.content_type_id is not None:
                pg_likes.append(lk)
            elif lk.resource_uuid:
                fuseki_uuids.append(str(lk.resource_uuid))

        # Collect PG resource UUIDs for hydration
        pg_uuids = []
        for lk in pg_likes:
            if lk.resource_uuid:
                pg_uuids.append(str(lk.resource_uuid))
            else:
                rc = ResourceContent.objects.filter(pk=lk.object_id).first()
                if rc:
                    pg_uuids.append(str(rc.resource.uuid))

        pg_items = postgres_hydrate(pg_uuids) if pg_uuids else []

        fuseki_items = []
        if fuseki_uuids:
            try:
                fuseki_items = (
                    get_metadata_for_learning_resources([lr_uri_ref(u) for u in fuseki_uuids]) or []
                )
            except Exception:
                pass

        # Merge preserving like order from qs_page
        pg_by_uuid = {str(i.id): i for i in pg_items}
        fuseki_by_uuid = {str(i.id): i for i in fuseki_items}
        ordered_items = []
        for lk in qs_page:
            uuid_str = str(lk.resource_uuid) if lk.resource_uuid else None
            if not uuid_str and lk.content_type_id is not None:
                rc = ResourceContent.objects.filter(pk=lk.object_id).first()
                if rc:
                    uuid_str = str(rc.resource.uuid)
            if uuid_str:
                item = pg_by_uuid.get(uuid_str) or fuseki_by_uuid.get(uuid_str)
                if item:
                    ordered_items.append(item)

        serializer = serializers.ItemSerializer(ordered_items, many=True)
        has_next = (page * PAGE_SIZE) < total
        has_prev = page > 1
        return Response(
            {
                "count": total,
                "next": f"?page={page + 1}" if has_next else None,
                "previous": f"?page={page - 1}" if has_prev else None,
                "results": serializer.data,
            }
        )


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
        from django.db.models import Count as DjCount

        request_serializer = serializers.ItemSearchRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        search_result = search_items_comprehensive(request_serializer.validated_data)

        # Enrich results with real likes count and interaction state for authenticated users
        results = search_result.results
        uuid_list = [str(item.id) for item in results if item.id]
        if uuid_list:
            like_counts = {
                str(row["resource_uuid"]): row["cnt"]
                for row in LikeModel.objects.filter(resource_uuid__in=uuid_list)
                .values("resource_uuid")
                .annotate(cnt=DjCount("id"))
            }
            for item in results:
                item.likes = like_counts.get(str(item.id), 0)

            if request.user.is_authenticated:
                user_bookmarks = set(
                    str(u)
                    for u in BookmarkModel.objects.filter(
                        user=request.user, resource_uuid__in=uuid_list
                    ).values_list("resource_uuid", flat=True)
                )
                user_likes = set(
                    str(u)
                    for u in LikeModel.objects.filter(
                        user=request.user, resource_uuid__in=uuid_list
                    ).values_list("resource_uuid", flat=True)
                )
                for item in results:
                    item.is_bookmarked = str(item.id) in user_bookmarks
                    item.is_liked = str(item.id) in user_likes

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


class CommunityViewEventView(APIView):
    """
    POST /v1/communities/<uuid:community_id>/view/

    Records a view event for a community page.
    Deduplicates per authenticated user or anonymous session within a 24-hour window.
    """

    permission_classes = [AllowAny]
    authentication_classes = [CsrfExemptSessionAuthentication]

    def post(self, request: Request, community_id: UUID) -> HttpResponse:
        from django.utils import timezone
        from datetime import timedelta

        fuseki_uri = f"https://id.dalia.education/community/{community_id}"
        pg = (
            PgCommunity.objects.filter(uri=fuseki_uri).first()
            or PgCommunity.objects.filter(uuid=community_id).first()
        )
        if not pg:
            return HttpResponseNotFound()

        user = request.user if request.user.is_authenticated else None
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key or ""

        cutoff = timezone.now() - timedelta(hours=24)
        content_type = ContentType.objects.get_for_model(PgCommunity)

        already_viewed = False
        if user:
            already_viewed = ViewEvent.objects.filter(
                content_type=content_type,
                object_id=pg.pk,
                user=user,
                created__gte=cutoff,
            ).exists()
        elif session_key:
            already_viewed = ViewEvent.objects.filter(
                content_type=content_type,
                object_id=pg.pk,
                session_id=session_key,
                created__gte=cutoff,
            ).exists()

        if not already_viewed:
            log_view_event(
                user=user,
                content_object=pg,
                session_id=session_key,
                ip_address=request.META.get("REMOTE_ADDR", ""),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
            return Response(status=201)

        return Response(status=204)


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

            pg_views = ViewEvent.objects.filter(
                content_type=ContentType.objects.get_for_model(PgCommunity),
                object_id=pg.pk,
            ).count()
            community = ApiCommunity(
                id=str(community_id),
                slug=pg.slug or slugify(pg.title),
                title=pg.title,
                image=pg.image or (fuseki_data.image if fuseki_data else None),
                url=pg.website_url or (fuseki_data.url if fuseki_data else "") or "",
                about=pg.description or (fuseki_data.about if fuseki_data else "") or "",
                likes=0,
                views=pg_views,
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

            pg_items = postgres_hydrate([str(u) for u in resource_uuids]) if resource_uuids else []

            # TODO: Remove this Fuseki fallback once PG is the sole database for resource content.
            # Always check Fuseki for resources linked to this community's URI and merge with PG.
            # Both sources use the same UUID as item.id, so deduplication is exact.
            fuseki_items = []
            if pg.uri:
                fuseki_resource_uri_refs = get_resources_for_community(URIRef(pg.uri))
                if fuseki_resource_uri_refs:
                    fuseki_items = (
                        get_metadata_for_learning_resources(fuseki_resource_uri_refs) or []
                    )

            if pg_items or fuseki_items:
                # PG items take priority; append Fuseki items not already present (same UUID = same resource).
                pg_ids = {item.id for item in pg_items}
                extra = [item for item in fuseki_items if item.id not in pg_ids]
                merged = pg_items + extra
                if merged:
                    from django.db.models import Count as DjCount
                    from curation.models import Like as LikeModel

                    uuid_list = [str(item.id) for item in merged if item.id]
                    like_counts = {
                        str(row["resource_uuid"]): row["cnt"]
                        for row in LikeModel.objects.filter(resource_uuid__in=uuid_list)
                        .values("resource_uuid")
                        .annotate(cnt=DjCount("id"))
                    }
                    for item in merged:
                        item.likes = like_counts.get(str(item.id), 0)
                serializer = serializers.ItemSerializer(merged, many=True)
                return Response(serializer.data)

            # Community exists but has no linked resources in either PG or Fuseki.
            return Response([])

        # Community not found in PG — fall back to Fuseki-only path for legacy data.
        items = get_items_for_community(community_id)
        if items is None:
            return HttpResponseNotFound()

        if items:
            from django.db.models import Count as DjCount
            from curation.models import Like as LikeModel

            uuid_list = [str(item.id) for item in items if item.id]
            like_counts = {
                str(row["resource_uuid"]): row["cnt"]
                for row in LikeModel.objects.filter(resource_uuid__in=uuid_list)
                .values("resource_uuid")
                .annotate(cnt=DjCount("id"))
            }
            for item in items:
                item.likes = like_counts.get(str(item.id), 0)
        serializer = serializers.ItemSerializer(items, many=True)
        return Response(serializer.data)


class DisciplineChildrenView(APIView):
    """Return sub-disciplines of a parent discipline with counts in the current search context.

    GET /api/v1/disciplines/children/?parent=<uri>&query=<q>&<facet_key>=<value>…

    Counts are computed over the PG filtered queryset using the same filters as
    the main search (query text + selected facets + date range).  Fuseki-only
    resources are not counted here (acceptable approximation for sidebar counts).
    """

    permission_classes = [AllowAny]

    def get(self, request):
        from curation.models import Discipline as DisciplineModel
        from search.api_models.api_models import ItemSearchRequest, SelectedFacet
        from search.query.items.search.text_search import _ITEM_SEARCH_FACETS_MAPPED_BY_KEY
        from search.query.items.search.producers.postgres_producer import (
            _base_queryset,
            _apply_date_filters,
            _apply_facet_filters,
            _apply_text_query,
        )
        from rdflib import URIRef
        from django.db.models import Count as DjCount

        parent_uri = request.query_params.get("parent", "").strip()
        if not parent_uri:
            return Response({"error": "parent parameter required"}, status=400)

        try:
            parent = DisciplineModel.objects.get(uri=parent_uri, is_active=True)
        except DisciplineModel.DoesNotExist:
            return Response([], status=200)

        children = list(
            DisciplineModel.objects.filter(parent_id=parent, is_active=True).order_by("label")
        )
        if not children:
            return Response([], status=200)

        child_uris = {c.uri for c in children if c.uri}

        # Parse search context from query params
        query = request.query_params.get("query", "*") or "*"
        date_after = request.query_params.get("datePublished_after")
        date_before = request.query_params.get("datePublished_before")

        _non_facet_keys = {
            "parent",
            "query",
            "offset",
            "limit",
            "source",
            "sortBy",
            "sortOrder",
            "datePublished_after",
            "datePublished_before",
        }
        selected_facets = []
        for key, values in request.query_params.lists():
            if key in _non_facet_keys:
                continue
            if URIRef(key) in _ITEM_SEARCH_FACETS_MAPPED_BY_KEY:
                selected_facets.append(SelectedFacet(key=key, selected=list(values)))

        fake_req = ItemSearchRequest(
            query=query,
            selectedFacets=selected_facets,
            limit=10000,
            offset=0,
            datePublished_after=date_after,
            datePublished_before=date_before,
        )

        # PG counts: use ORM annotation for distinct resource count per child discipline.
        qs = _base_queryset()
        qs = _apply_date_filters(qs, fake_req)
        qs = _apply_facet_filters(qs, fake_req)
        qs, _ = _apply_text_query(qs, query)

        pg_counts: dict = {}
        from search.query.items.search.producers.postgres_producer import _get_disc_descendants_map

        _desc_map = _get_disc_descendants_map()
        for child in children:
            if not child.uri:
                continue
            _child_desc = list(_desc_map.get(child.uri, frozenset({child.uri})))
            _cnt = qs.filter(disciplines__uri__in=_child_desc).distinct().count()
            if _cnt:
                pg_counts[child.uri] = _cnt

        # Fuseki counts: count distinct Fuseki-only resources per child discipline.
        fuseki_counts: dict = {}
        enabled_sources = get_enabled_search_sources()
        if "fuseki" in enabled_sources:
            try:
                from search.query.items.search.comprehensive_search import (
                    _get_matching_uris,
                    _fetch_facet_values,
                )
                from search.query.items.facets.active_facets_extraction import (
                    extract_active_facets_from_selected_facets,
                )
                from search.rdf.namespace import fabio as _fabio

                active_facets = extract_active_facets_from_selected_facets(
                    selected_facets, _ITEM_SEARCH_FACETS_MAPPED_BY_KEY
                )
                all_fuseki_uris = _get_matching_uris(
                    text_query=query,
                    active_facets=active_facets,
                    sort_by="relevance",
                    sort_order="dsc",
                    date_published_after=date_after,
                    date_published_before=date_before,
                )
                if all_fuseki_uris:
                    disc_values = _fetch_facet_values(all_fuseki_uris, [_fabio.hasDiscipline])
                    from collections import defaultdict as _dd

                    _fuseki_lr_per_child: dict = _dd(set)
                    for _lr, disc_node in disc_values:
                        _disc_str = str(disc_node)
                        _lr_str = str(_lr)
                        for _child_uri in child_uris:
                            if _disc_str in _desc_map.get(_child_uri, frozenset({_child_uri})):
                                _fuseki_lr_per_child[_child_uri].add(_lr_str)
                                break
                    fuseki_counts = {k: len(v) for k, v in _fuseki_lr_per_child.items()}
            except Exception as exc:
                import logging as _logging

                _logging.getLogger(__name__).warning(
                    "DisciplineChildrenView: Fuseki count failed: %s", exc
                )

        result = [
            {
                "label": child.label,
                "value": child.uri,
                "count": pg_counts.get(child.uri, 0) + fuseki_counts.get(child.uri, 0),
                "active": False,
                "hasChildren": False,
            }
            for child in children
            if child.uri is not None
        ]
        return Response(result)
