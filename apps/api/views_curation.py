from curation import models as cf
from curation import services as cf_services
from django.db.models import Q
from django.http import Http404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .serializers_curation import (
    BookmarkSerializer,
    CommunityMembershipSerializer,
    CommunitySerializer,
    CommunityWriteSerializer,
    DisciplineSerializer,
    EditLogSerializer,
    FileFormatSerializer,
    LanguageSerializer,
    LearningResourceTypeSerializer,
    LicenseSerializer,
    LikeSerializer,
    MediaTypeSerializer,
    OrganizationSerializer,
    PersonSerializer,
    ProficiencyLevelSerializer,
    RelationTypeCategorySerializer,
    RelationTypeSerializer,
    ResourceCommunityRelationSerializer,
    ResourceConsentSerializer,
    ResourceContentReadSerializer,
    ResourceContentWriteSerializer,
    ResourceLinkSerializer,
    ResourcePublishingConsentSerializer,
    ResourceRelatedItemSerializer,
    ResourceSerializer,
    ReviewQuestionSerializer,
    ReviewReadSerializer,
    ReviewWriteSerializer,
    TargetGroupSerializer,
    ViewEventSerializer,
)


# -------------------- shared mixins --------------------
class _NameSearchMixin:
    """Adds ?search=foo (tries 'label', 'name', 'title', or 'slug' if present)."""
    def get_queryset(self):
        qs = super().get_queryset()
        term = self.request.query_params.get("search")
        if not term:
            return qs
        model = qs.model
        names = {f.name for f in model._meta.get_fields()}
        cond = Q()
        if "label" in names:
            cond |= Q(label__icontains=term)
        if "name" in names:
            cond |= Q(name__icontains=term)
        if "title" in names:
            cond |= Q(title__icontains=term)
        if "slug" in names:
            cond |= Q(slug__icontains=term)
        return qs.filter(cond) if cond else qs.none()


class _ReadOnlyLookupViewset(_NameSearchMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    pagination_class = None
    lookup_field = 'uuid'

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs[lookup_url_kwarg]

        try:
            if self.lookup_field == 'uuid':
                return self.get_queryset().get(uuid=lookup_value)
            else:
                return self.get_queryset().get(pk=lookup_value)
        except (self.get_queryset().model.DoesNotExist, ValueError):
            try:
                return self.get_queryset().get(pk=lookup_value)
            except (self.get_queryset().model.DoesNotExist, ValueError) as err:
                raise Http404(f"{self.get_queryset().model._meta.verbose_name} not found") from err

    @extend_schema(
        parameters=[OpenApiParameter(
            name="search", location=OpenApiParameter.QUERY, required=False,
            description="Case-insensitive filter on name/title.", type=str
        )]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class _EditableLookupViewset(_NameSearchMixin, viewsets.ModelViewSet):
    """
    Base class for vocabulary ViewSets that need CREATE operations.
    Supports UUID lookups and allows POST, PUT, PATCH operations.
    Public READ access for vocabularies, authenticated WRITE access.
    """
    pagination_class = None
    lookup_field = 'uuid'

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs[lookup_url_kwarg]

        try:
            if self.lookup_field == 'uuid':
                return self.get_queryset().get(uuid=lookup_value)
            else:
                return self.get_queryset().get(pk=lookup_value)
        except (self.get_queryset().model.DoesNotExist, ValueError):
            try:
                return self.get_queryset().get(pk=lookup_value)
            except (self.get_queryset().model.DoesNotExist, ValueError) as err:
                raise Http404(f"{self.get_queryset().model._meta.verbose_name} not found") from err

    @extend_schema(
        parameters=[OpenApiParameter(
            name="search", location=OpenApiParameter.QUERY, required=False,
            description="Case-insensitive filter on name/title.", type=str
        )]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


# -------------------- vocab viewsets (read-only) --------------------
@extend_schema(tags=["Curation - Communities"], summary="Communities")
class CommunityViewSet(_EditableLookupViewset):
    queryset = cf.Community.objects.all().order_by("id")
    serializer_class = CommunitySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def create(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        write_serializer = CommunityWriteSerializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        community = write_serializer.save()
        cf.CommunityMembership.objects.create(
            user=request.user,
            community=community,
            role='owner',
            is_approved=True,
            approved_by=request.user,
        )
        read_serializer = CommunitySerializer(community)
        headers = self.get_success_headers(write_serializer.data)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED, headers=headers)


@extend_schema(tags=["Curation - Disciplines"], summary="Disciplines")
class DisciplineViewSet(_EditableLookupViewset):
    queryset = cf.Discipline.objects.select_related('parent_id').all().order_by("label")
    serializer_class = DisciplineSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        parent_id = self.request.query_params.get('parent_id')

        if parent_id == 'null' or parent_id == '':
            qs = qs.filter(parent_id__isnull=True)
        elif parent_id:
            qs = qs.filter(parent_id=parent_id)

        return qs

    @extend_schema(
        summary="Get root disciplines",
        description="Get all top-level disciplines (where parent_id is NULL)",
        responses={200: OpenApiResponse(response=DisciplineSerializer(many=True))}
    )
    @action(detail=False, methods=["get"], url_path="roots")
    def roots(self, request):
        root_disciplines = cf.Discipline.get_root_disciplines().order_by("label")
        serializer = self.get_serializer(root_disciplines, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get children of discipline",
        description="Get direct children of specified discipline",
        responses={200: OpenApiResponse(response=DisciplineSerializer(many=True))}
    )
    @action(detail=True, methods=["get"], url_path="children")
    def children(self, request, uuid=None, **kwargs):
        discipline = self.get_object()
        children = discipline.get_children().order_by("label")
        serializer = self.get_serializer(children, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get descendants of discipline",
        description="Get all descendants (recursive children) of specified discipline",
        responses={200: OpenApiResponse(response=DisciplineSerializer(many=True))}
    )
    @action(detail=True, methods=["get"], url_path="descendants")
    def descendants(self, request, uuid=None, **kwargs):
        discipline = self.get_object()
        descendants = discipline.get_descendants()
        serializer = self.get_serializer(descendants, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get ancestors of discipline",
        description="Get all ancestors (recursive parents) of specified discipline",
        responses={200: OpenApiResponse(response=DisciplineSerializer(many=True))}
    )
    @action(detail=True, methods=["get"], url_path="ancestors")
    def ancestors(self, request, uuid=None, **kwargs):
        discipline = self.get_object()
        ancestors = discipline.get_ancestors()
        serializer = self.get_serializer(ancestors, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get hierarchy tree",
        description="Get complete hierarchy tree starting from roots",
        responses={200: OpenApiResponse(description="Nested hierarchy structure")}
    )
    @action(detail=False, methods=["get"], url_path="tree")
    def tree(self, request):
        def build_tree_node(discipline):
            children = discipline.get_children().order_by("label")
            return {
                'id': discipline.pk,
                'uuid': str(discipline.uuid),
                'label': discipline.label,
                'slug': discipline.slug,
                'uri': discipline.uri,
                'parent_id': discipline.parent_id.pk if discipline.parent_id else None,
                'parent_label': discipline.parent_label,
                'level': discipline.get_level(),
                'children_count': len(children),
                'children': [build_tree_node(child) for child in children] if children else []
            }

        root_disciplines = cf.Discipline.get_root_disciplines().order_by("label")
        tree_data = [build_tree_node(root) for root in root_disciplines]

        return Response({
            'tree': tree_data,
            'total_roots': len(tree_data)
        })


@extend_schema(tags=["Curation - File formats"], summary="File formats")
class FileFormatViewSet(_EditableLookupViewset):
    queryset = cf.FileFormat.objects.all().order_by("id")
    serializer_class = FileFormatSerializer


@extend_schema(tags=["Curation - Learning resource types"], summary="Learning resource types")
class LearningResourceTypeViewSet(_EditableLookupViewset):
    queryset = cf.LearningResourceType.objects.all().order_by("id")
    serializer_class = LearningResourceTypeSerializer


@extend_schema(tags=["Curation - Licenses"], summary="Licenses")
class LicenseViewSet(_EditableLookupViewset):
    queryset = cf.License.objects.all().order_by("id")
    serializer_class = LicenseSerializer


@extend_schema(tags=["Curation - Media types"], summary="Media types")
class MediaTypeViewSet(_EditableLookupViewset):
    queryset = cf.MediaType.objects.all().order_by("id")
    serializer_class = MediaTypeSerializer


@extend_schema(tags=["Curation - Languages"], summary="Languages")
class LanguageViewSet(_EditableLookupViewset):
    queryset = cf.Language.objects.all().order_by("code")
    serializer_class = LanguageSerializer


@extend_schema(tags=["Curation - Organizations"], summary="Organizations")
class OrganizationViewSet(_EditableLookupViewset):
    queryset = cf.Organization.objects.all().order_by("id")
    serializer_class = OrganizationSerializer


@extend_schema(tags=["Curation - Persons"], summary="Persons")
class PersonViewSet(_EditableLookupViewset):
    queryset = cf.Person.objects.all().order_by("id")
    serializer_class = PersonSerializer

    def get_queryset(self):
        # Bypass _NameSearchMixin since Person doesn't have standard label/name/title/slug fields
        qs = self.queryset.all()
        search_term = self.request.query_params.get("search")

        if search_term:
            qs = qs.filter(
                Q(first_name__icontains=search_term) |
                Q(last_name__icontains=search_term) |
                Q(orcid__icontains=search_term)
            )

        # Enforce privacy: public profiles visible to all; own profile always accessible
        # (so authenticated users can view/edit their own non-public profile via preferences)
        user = self.request.user
        if user.is_authenticated and user.is_superuser:
            return qs

        if user.is_authenticated:
            # Logged-in users see public + internal profiles
            privacy_filter = Q(privacy_level='public') | Q(privacy_level='internal')
            try:
                own_person = cf.Person.objects.get(user=user)
                privacy_filter |= Q(id=own_person.id)
            except cf.Person.DoesNotExist:
                pass
        else:
            # Anonymous visitors see only public profiles
            privacy_filter = Q(privacy_level='public')

        return qs.filter(privacy_filter)

    @extend_schema(
        summary="Get person by ORCID",
        description="Retrieve a person record using their ORCID identifier.",
        responses={
            200: OpenApiResponse(response=PersonSerializer, description="Person found"),
            404: OpenApiResponse(description="Person with this ORCID not found")
        },
    )
    @action(detail=False, methods=["get"], url_path="orcid/(?P<orcid>[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X])")
    def by_orcid(self, request, orcid=None):
        try:
            person = self.get_queryset().get(orcid=orcid)
            serializer = self.get_serializer(person)
            return Response(serializer.data)
        except cf.Person.DoesNotExist as err:
            raise Http404(f"Person with ORCID {orcid} not found") from err


@extend_schema(tags=["Curation - Proficiency levels"], summary="Proficiency levels")
class ProficiencyLevelViewSet(_EditableLookupViewset):
    queryset = cf.ProficiencyLevel.objects.all().order_by("id")
    serializer_class = ProficiencyLevelSerializer


@extend_schema(tags=["Curation - Target groups"], summary="Target groups")
class TargetGroupViewSet(_EditableLookupViewset):
    queryset = cf.TargetGroup.objects.all().order_by("id")
    serializer_class = TargetGroupSerializer


# -------------------- Resources & draft contents --------------------
@extend_schema(
    tags=["Curation - Resources"],
    summary="Resources (grouper)",
    description="Exposes resource grouper objects. Supports UUID-based lookups."
)
class ResourceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Exposes the grouper object. Creation happens implicitly from ResourceContentViewSet.
    Public READ access (read-only ViewSet).
    """
    queryset = cf.Resource.objects.all().order_by("-id")
    serializer_class = ResourceSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'uuid'

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs[lookup_url_kwarg]

        try:
            if self.lookup_field == 'uuid':
                return self.get_queryset().get(uuid=lookup_value)
            else:
                return self.get_queryset().get(pk=lookup_value)
        except (cf.Resource.DoesNotExist, ValueError):
            try:
                return self.get_queryset().get(pk=lookup_value)
            except (cf.Resource.DoesNotExist, ValueError) as err:
                raise Http404("Resource not found") from err


class ContributionsPagination(PageNumberPagination):
    page_size = 9
    page_size_query_param = 'page_size'
    max_page_size = 9


@extend_schema(
    tags=["Curation - Resource contents"],
    summary="Resource contents (versions)",
    description="Create/update DRAFT content versions. Supports UUID-based lookups."
)
class ResourceContentViewSet(viewsets.ModelViewSet):
    """
    Create/update DRAFT content versions.
    Curators/admins see all; regular users see their own drafts + published.
    Anonymous users see only published content.
    """
    queryset = cf.ResourceContent.objects.select_related("resource").all().order_by("-id")
    lookup_field = 'uuid'
    pagination_class = ContributionsPagination

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs[lookup_url_kwarg]

        try:
            if self.lookup_field == 'uuid':
                return self.get_queryset().get(uuid=lookup_value)
            else:
                return self.get_queryset().get(pk=lookup_value)
        except (cf.ResourceContent.DoesNotExist, ValueError):
            try:
                return self.get_queryset().get(pk=lookup_value)
            except (cf.ResourceContent.DoesNotExist, ValueError) as err:
                raise Http404("Resource content not found") from err

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return ResourceContentReadSerializer
        return ResourceContentWriteSerializer

    def get_queryset(self):
        user = self.request.user
        qs = cf.ResourceContent.objects.select_related("resource").all().order_by("-id")

        filter_param = self.request.query_params.get('filter', 'my-resources') if self.action == 'list' else 'my-resources'
        show_all_param = self.request.query_params.get('show_all', 'false').lower() == 'true'

        # Curators/superusers with show_all=true: see all content
        if show_all_param and user.is_authenticated and (
            user.is_superuser or user.groups.filter(name="Curators").exists()
        ):
            if filter_param == 'archived':
                return qs.filter(resource__is_removed=True)
            if filter_param == 'published':
                return qs.filter(is_active=True, resource__is_published=True, resource__is_removed=False)
            if filter_param == 'pending':
                return qs.filter(submitted_for_review=True, resource__is_removed=False)
            if filter_param == 'unpublished':
                return qs.filter(
                    submitted_for_review=False,
                    resource__is_removed=False
                ).filter(
                    Q(resource__is_published=True, is_active=False) |
                    Q(resource__is_published=False, is_active=True)
                )
            return qs.filter(resource__is_removed=False)

        # Authenticated users: only their own content, filtered by state
        if user.is_authenticated:
            base = qs.filter(created_by=user)

            if filter_param in ('my-resources', 'all'):
                return base.filter(resource__is_removed=False)

            if filter_param == 'published':
                return base.filter(is_active=True, resource__is_published=True, resource__is_removed=False)

            if filter_param == 'pending':
                return base.filter(submitted_for_review=True, resource__is_removed=False)

            if filter_param == 'unpublished':
                return base.filter(
                    submitted_for_review=False,
                    resource__is_removed=False
                ).filter(
                    Q(resource__is_published=True, is_active=False) |
                    Q(resource__is_published=False, is_active=True)
                )

            if filter_param == 'archived':
                return base.filter(resource__is_removed=True)

            if filter_param == 'all-resources':
                return qs.filter(is_active=True, resource__is_published=True, resource__is_removed=False)

            # default fallback: same as my-resources
            return base.filter(resource__is_removed=False)

        # Anonymous: only published, active, non-removed
        return qs.filter(resource__is_published=True, resource__is_removed=False, is_active=True)

    @extend_schema(
        summary="Create a new DRAFT content (and grouper if needed)",
        description=(
            "POST a ResourceContent payload. "
            "If 'resource' is omitted, a new Resource grouper is created automatically. "
            "Returns the created DRAFT content."
        ),
        responses={201: OpenApiResponse(response=ResourceContentReadSerializer)},
    )
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        resource_ref = data.get("resource")
        if not resource_ref:
            title = data.get("title", "")
            resource = cf.Resource.objects.create(owner=request.user, title=title)
            data["resource"] = resource.pk
        else:
            # Accept UUID string (from frontend edit-as-new-version flow) or integer PK
            try:
                int(resource_ref)  # already a PK — leave as-is
            except (ValueError, TypeError):
                try:
                    res = cf.Resource.objects.get(uuid=resource_ref)
                    data["resource"] = res.pk
                except cf.Resource.DoesNotExist:
                    return Response({"resource": ["Resource not found."]}, status=400)

        # Add required user fields to data before validation
        data['created_by'] = request.user.pk

        # Handle submission for review
        if data.get('submitted_for_review'):
            data['submitted_by'] = request.user.pk
            data['submitted_at'] = timezone.now().isoformat()

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        read = ResourceContentReadSerializer(instance, context={"request": request})
        headers = self.get_success_headers(read.data)
        return Response(read.data, status=status.HTTP_201_CREATED, headers=headers)

    @extend_schema(
        summary="Submit a DRAFT for review",
        description="Flags this draft for curators. Stays in DRAFT state (no publish).",
        responses={200: OpenApiResponse(description="Marked for review")},
    )
    @action(detail=True, methods=["post"], url_path="submit-for-review")
    def submit_for_review(self, request, uuid=None):
        content = self.get_object()
        cf_services.submit_for_review(content, request.user)
        return Response({"ok": True, "submitted_for_review": True})

    @extend_schema(
        summary="Soft delete a Resource (curators only)",
        description="Marks the grouper as removed; keeps history intact.",
        responses={200: OpenApiResponse(description="Marked as removed")},
    )
    @action(detail=True, methods=["post"], url_path="soft-delete")
    def soft_delete(self, request, uuid=None):
        content = self.get_object()
        is_curator = request.user.is_superuser or request.user.groups.filter(name="Curators").exists()
        # Owners may delete their own unpublished drafts; curators may delete anything
        is_owner_of_draft = (
            content.created_by == request.user
            and not content.resource.is_published
        )
        if not (is_curator or is_owner_of_draft):
            return Response({"detail": "Not permitted"}, status=403)
        cf_services.soft_delete(content.resource, request.user)
        return Response({"ok": True, "removed": True})


# -------------------- New Models ViewSets --------------------

@extend_schema(
    tags=["Curation - Community Management"],
    summary="Community memberships",
    description="Manage community memberships and roles."
)
class CommunityMembershipViewSet(viewsets.ModelViewSet):
    queryset = cf.CommunityMembership.objects.select_related("user", "community").all().order_by("-id")
    serializer_class = CommunityMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if user.is_superuser:
            return qs

        admin_communities = cf.CommunityMembership.objects.filter(
            user=user, role__in=['admin', 'owner']
        ).values_list('community_id', flat=True)

        if admin_communities:
            return qs.filter(
                Q(user=user) | Q(community_id__in=admin_communities)
            ).distinct()

        return qs.filter(user=user)

    @extend_schema(
        summary="Approve pending memberships",
        description="Approve selected membership requests (community admins only).",
        responses={200: OpenApiResponse(description="Memberships approved")}
    )
    @action(detail=True, methods=["post"], url_path="approve")
    def approve_membership(self, request, pk=None):
        membership = self.get_object()

        if not membership.community.user_can_admin(request.user):
            return Response({"detail": "Not permitted"}, status=403)

        membership.approve_membership(request.user)
        return Response({"ok": True, "approved": True})

    @extend_schema(
        summary="Promote member role",
        description="Promote member to moderator (community admins only).",
        responses={200: OpenApiResponse(description="Member promoted")}
    )
    @action(detail=True, methods=["post"], url_path="promote")
    def promote_member(self, request, pk=None):
        membership = self.get_object()
        new_role = request.data.get('role', 'moderator')

        if not membership.community.user_can_admin(request.user):
            return Response({"detail": "Not permitted"}, status=403)

        membership.promote_to(new_role, request.user)
        return Response({"ok": True, "promoted": True, "new_role": new_role})


@extend_schema(
    tags=["Curation - User Interactions"],
    summary="User bookmarks",
    description="Personal bookmark management."
)
class BookmarkViewSet(viewsets.ModelViewSet):
    queryset = cf.Bookmark.objects.select_related("content_type").all().order_by("-id")
    serializer_class = BookmarkSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        summary="Toggle bookmark",
        description="Add or remove bookmark for given content object.",
        responses={200: OpenApiResponse(description="Bookmark toggled")}
    )
    @action(detail=False, methods=["post"], url_path="toggle")
    def toggle_bookmark(self, request):
        content_type_id = request.data.get('content_type')
        object_id = request.data.get('object_id')

        if not content_type_id or not object_id:
            return Response({"detail": "content_type and object_id required"}, status=400)

        bookmark, created = cf.Bookmark.objects.get_or_create(
            user=request.user,
            content_type_id=content_type_id,
            object_id=object_id
        )

        if not created:
            bookmark.delete()
            return Response({"ok": True, "bookmarked": False})

        return Response({"ok": True, "bookmarked": True})


@extend_schema(
    tags=["Curation - User Interactions"],
    summary="User likes",
    description="User likes/favorites management."
)
class LikeViewSet(viewsets.ModelViewSet):
    queryset = cf.Like.objects.select_related("content_type").all().order_by("-id")
    serializer_class = LikeSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        summary="Toggle like",
        description="Add or remove like for given content object.",
        responses={200: OpenApiResponse(description="Like toggled")}
    )
    @action(detail=False, methods=["post"], url_path="toggle")
    def toggle_like(self, request):
        content_type_id = request.data.get('content_type')
        object_id = request.data.get('object_id')

        if not content_type_id or not object_id:
            return Response({"detail": "content_type and object_id required"}, status=400)

        like, created = cf.Like.objects.get_or_create(
            user=request.user,
            content_type_id=content_type_id,
            object_id=object_id
        )

        if not created:
            like.delete()
            return Response({"ok": True, "liked": False})

        return Response({"ok": True, "liked": True})


@extend_schema(
    tags=["Curation - Analytics"],
    summary="View events (Admin only)",
    description="Analytics view events - read-only access for administrators."
)
class ViewEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = cf.ViewEvent.objects.select_related("content_type").all().order_by("-id")
    serializer_class = ViewEventSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'uuid'


@extend_schema(
    tags=["Curation - Analytics"],
    summary="Edit logs (Admin only)",
    description="Audit trail edit logs - read-only access for administrators."
)
class EditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = cf.EditLog.objects.select_related("content_type").all().order_by("-id")
    serializer_class = EditLogSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'uuid'


@extend_schema(
    tags=["Curation - Review System"],
    summary="Reviews",
    description="Review management. Reviewers see their reviews, moderators see community reviews."
)
class ReviewViewSet(viewsets.ModelViewSet):
    queryset = cf.Review.objects.select_related("resource_content", "reviewer", "community").all().order_by("-id")
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return ReviewReadSerializer
        return ReviewWriteSerializer

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if user.is_superuser:
            return qs

        moderated_communities = cf.CommunityMembership.objects.filter(
            user=user, role__in=['moderator', 'admin', 'owner']
        ).values_list('community_id', flat=True)

        if moderated_communities:
            return qs.filter(
                Q(reviewer=user) | Q(community_id__in=moderated_communities)
            ).distinct()

        return qs.filter(reviewer=user)

    def perform_create(self, serializer):
        serializer.save(reviewer=self.request.user)

    @extend_schema(
        summary="Submit review",
        description="Submit review for approval.",
        responses={200: OpenApiResponse(description="Review submitted")}
    )
    @action(detail=True, methods=["post"], url_path="submit")
    def submit_review(self, request, pk=None):
        review = self.get_object()

        if review.reviewer != request.user:
            return Response({"detail": "Not permitted"}, status=403)

        review.status = 'submitted'
        review.submitted_at = timezone.now()
        review.save()
        return Response({"ok": True, "submitted": True})

    @extend_schema(
        summary="Approve review",
        description="Approve review (moderators only).",
        responses={200: OpenApiResponse(description="Review approved")}
    )
    @action(detail=True, methods=["post"], url_path="approve")
    def approve_review(self, request, pk=None):
        review = self.get_object()

        if not (review.community and review.community.user_can_moderate(request.user)):
            return Response({"detail": "Not permitted"}, status=403)

        review.status = 'approved'
        review.completed_at = timezone.now()
        review.save()
        return Response({"ok": True, "approved": True})


@extend_schema(
    tags=["Curation - Review System"],
    summary="Review questions",
    description="Review question configuration (community admins and moderators)."
)
class ReviewQuestionViewSet(viewsets.ModelViewSet):
    queryset = cf.ReviewQuestion.objects.select_related("community").all().order_by("community", "order")
    serializer_class = ReviewQuestionSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if user.is_superuser:
            return qs

        managed_communities = cf.CommunityMembership.objects.filter(
            user=user, role__in=['moderator', 'admin', 'owner']
        ).values_list('community_id', flat=True)

        if managed_communities:
            return qs.filter(
                Q(community__isnull=True) |
                Q(community_id__in=managed_communities)
            )

        return qs.filter(community__isnull=True)

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        if obj.community:
            return obj.community.user_can_moderate(request.user)
        return request.user.is_superuser


# -------------------- Legal Compliance --------------------

@extend_schema(
    tags=["Curation - Legal Compliance"],
    summary="Resource consents",
    description="GDPR consent tracking."
)
class ResourceConsentViewSet(viewsets.ModelViewSet):
    queryset = cf.ResourceConsent.objects.select_related("resource_content", "person").all().order_by("-id")
    serializer_class = ResourceConsentSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if user.is_superuser:
            return qs

        try:
            person = cf.Person.objects.get(user=user)
            return qs.filter(person=person)
        except cf.Person.DoesNotExist:
            return qs.none()

    @extend_schema(
        summary="Grant consent",
        description="Grant consent with audit trail.",
        responses={200: OpenApiResponse(description="Consent granted")}
    )
    @action(detail=True, methods=["post"], url_path="grant")
    def grant_consent(self, request, pk=None):
        consent = self.get_object()

        if consent.person.user != request.user and not request.user.is_superuser:
            return Response({"detail": "Not permitted"}, status=403)

        consent_text = request.data.get('consent_text', '')
        version = request.data.get('version', '1.0')
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        consent.grant_consent(consent_text, version, ip_address, user_agent)
        return Response({"ok": True, "granted": True})

    @extend_schema(
        summary="Withdraw consent",
        description="Withdraw consent with reason.",
        responses={200: OpenApiResponse(description="Consent withdrawn")}
    )
    @action(detail=True, methods=["post"], url_path="withdraw")
    def withdraw_consent(self, request, pk=None):
        consent = self.get_object()

        if consent.person.user != request.user and not request.user.is_superuser:
            return Response({"detail": "Not permitted"}, status=403)

        reason = request.data.get('reason', '')
        consent.withdraw_consent(reason)
        return Response({"ok": True, "withdrawn": True})


@extend_schema(
    tags=["Curation - Legal Compliance"],
    summary="Publishing consents",
    description="Publishing consent management with GDPR compliance."
)
class ResourcePublishingConsentViewSet(viewsets.ModelViewSet):
    queryset = cf.ResourcePublishingConsent.objects.select_related("resource_content", "consenting_person").all().order_by("-id")
    serializer_class = ResourcePublishingConsentSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if user.is_superuser:
            return qs

        try:
            person = cf.Person.objects.get(user=user)
            return qs.filter(consenting_person=person)
        except cf.Person.DoesNotExist:
            return qs.none()

    @extend_schema(
        summary="Withdraw all consents",
        description="Withdraw all consents for this resource.",
        responses={200: OpenApiResponse(description="All consents withdrawn")}
    )
    @action(detail=True, methods=["post"], url_path="withdraw-all")
    def withdraw_all_consents(self, request, pk=None):
        consent = self.get_object()

        if consent.consenting_person.user != request.user and not request.user.is_superuser:
            return Response({"detail": "Not permitted"}, status=403)

        reason = request.data.get('reason', '')
        consent.withdraw_all(reason)
        return Response({"ok": True, "withdrawn": True})


# -------------------- Resource Relations --------------------

@extend_schema(
    tags=["Curation - Relation Types"],
    summary="Relation type categories",
    description="Categories for organizing relation types."
)
class RelationTypeCategoryViewSet(_EditableLookupViewset):
    queryset = cf.RelationTypeCategory.objects.filter(is_active=True).order_by("order", "name")
    serializer_class = RelationTypeCategorySerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(name="search", location=OpenApiParameter.QUERY, required=False,
                             description="Case-insensitive search on category name.", type=str),
            OpenApiParameter(name="ordering", location=OpenApiParameter.QUERY, required=False,
                             description="Order by: order, name, -order, -name", type=str)
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


@extend_schema(
    tags=["Curation - Relation Types"],
    summary="Relation types",
    description="Dynamic relation types with category organization."
)
class RelationTypeViewSet(_EditableLookupViewset):
    queryset = cf.RelationType.objects.filter(is_active=True).select_related("category").order_by("category__order", "order", "label")
    serializer_class = RelationTypeSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(name="search", location=OpenApiParameter.QUERY, required=False,
                             description="Case-insensitive search on relation type code or label.", type=str),
            OpenApiParameter(name="category_uuid", location=OpenApiParameter.QUERY, required=False,
                             description="Filter by category UUID (comma-separated for multiple).", type=str),
            OpenApiParameter(name="category", location=OpenApiParameter.QUERY, required=False,
                             description="Filter by category name (comma-separated for multiple).", type=str),
            OpenApiParameter(name="ordering", location=OpenApiParameter.QUERY, required=False,
                             description="Order by: order, label, code, -order, -label, -code", type=str)
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()

        category_uuid = self.request.query_params.get("category_uuid")
        if category_uuid:
            uuids = [uuid.strip() for uuid in category_uuid.split(',') if uuid.strip()]
            if uuids:
                qs = qs.filter(category__uuid__in=uuids)

        category_name = self.request.query_params.get("category")
        if category_name:
            names = [name.strip() for name in category_name.split(',') if name.strip()]
            if names:
                name_filters = Q()
                for name in names:
                    name_filters |= Q(category__name__icontains=name)
                qs = qs.filter(name_filters)

        ordering_param = self.request.query_params.get("ordering")
        if ordering_param:
            allowed_fields = ['order', 'label', 'code', '-order', '-label', '-code']
            if ordering_param in allowed_fields:
                qs = qs.order_by(ordering_param)

        return qs

    @extend_schema(
        parameters=[OpenApiParameter(
            name="category_uuid", location=OpenApiParameter.QUERY, required=False,
            description="Get relation types for specific category.", type=str
        )]
    )
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get relation types grouped by category."""
        categories = cf.RelationTypeCategory.objects.filter(is_active=True).prefetch_related('relation_types').order_by('order', 'name')
        result = []
        for category in categories:
            relation_types = category.relation_types.filter(is_active=True).order_by('order', 'label')
            result.append({
                'uuid': str(category.uuid),
                'name': category.name,
                'description': category.description,
                'color': category.color,
                'relation_types': RelationTypeSerializer(relation_types, many=True).data
            })
        return Response(result)


@extend_schema(
    tags=["Curation - Resource Relations"],
    summary="Resource links",
    description="External resource links management."
)
class ResourceLinkViewSet(viewsets.ModelViewSet):
    queryset = cf.ResourceLink.objects.select_related("content").all().order_by("-id")
    serializer_class = ResourceLinkSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'
    def get_queryset(self):
        qs = super().get_queryset()
        content_uuid = self.request.query_params.get('content')
        if content_uuid:
            qs = qs.filter(content__uuid=content_uuid)
        return qs



@extend_schema(
    tags=["Curation - Resource Relations"],
    summary="Community relations",
    description="Resource-community association management."
)
class ResourceCommunityRelationViewSet(viewsets.ModelViewSet):
    queryset = cf.ResourceCommunityRelation.objects.select_related("content", "community", "relation_type", "relation_type__category").all().order_by("-id")
    serializer_class = ResourceCommunityRelationSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'
    def get_queryset(self):
        qs = super().get_queryset()
        content_uuid = self.request.query_params.get('content')
        if content_uuid:
            qs = qs.filter(content__uuid=content_uuid)
        return qs



@extend_schema(
    tags=["Curation - Resource Relations"],
    summary="Related items",
    description="Resource relationship management."
)
class ResourceRelatedItemViewSet(viewsets.ModelViewSet):
    queryset = cf.ResourceRelatedItem.objects.select_related("content", "relation_type", "relation_type__category").all().order_by("-id")
    serializer_class = ResourceRelatedItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'
    def get_queryset(self):
        qs = super().get_queryset()
        content_uuid = self.request.query_params.get('content')
        if content_uuid:
            qs = qs.filter(content__uuid=content_uuid)
        return qs

