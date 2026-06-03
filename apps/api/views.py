from allauth.socialaccount.models import SocialAccount, SocialToken

# Import Person model from curation
from curation import models as cf
from django.contrib.auth import get_user_model
from django.db.models import Q

# Swagger
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import AuthProfileSerializer, PersonProfileSerializer, UserSerializer

User = get_user_model()


# ####### USER ############################
class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint to view or edit users. Only authenticated users can access this.
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Limit normal staff to non-superuser accounts, etc.
        if user.is_superuser:
            return User.objects.all()
        return User.objects.filter(id=user.id)


class AuthViewSet(viewsets.GenericViewSet):
    """
    API endpoint for identity-related actions of the authenticated user.
    """

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if getattr(self, "action", None) == "profile":
            return AuthProfileSerializer
        return self.serializer_class

    @extend_schema(
        summary="Get current authenticated user",
        description="Retrieve the authenticated user's details with groups and effective permissions.",
        responses={
            200: OpenApiResponse(
                response=UserSerializer, description="User details returned successfully."
            ),
            401: OpenApiResponse(
                description="Authentication credentials were not provided or invalid."
            ),
        },
        examples=[
            OpenApiExample(
                "Authenticated User Example",
                value={
                    "id": 1,
                    "username": "john_doe",
                    "email": "john@example.com",
                    "is_staff": True,
                    "is_superuser": False,
                    "groups": [{"id": 1, "name": "Editors"}],
                    "user_permissions": [],
                    "effective_permissions": ["blog.add_post", "blog.change_post"],
                },
                response_only=True,
            )
        ],
    )
    @action(detail=False, methods=["get"], url_path="me", url_name="me")
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @extend_schema(
        summary="Get authenticated user's social login profile and entitlements",
        description="Returns identity info, organizational role mappings, and token metadata for the authenticated user.",
        responses={
            200: OpenApiResponse(description="User profile from social account"),
            401: OpenApiResponse(description="Unauthorized"),
        },
    )
    @action(detail=False, methods=["get"], url_path="profile")
    def profile(self, request):
        user = request.user
        sa = SocialAccount.objects.filter(
            user=user, provider=request.session.get("last_social_provider")
        ).first()
        token = SocialToken.objects.filter(account=sa).first() if sa else None
        raw_extra = sa.extra_data if sa else {}
        # Normalize: allauth v65+ nests claims under extra_data["userinfo"];
        # older records store claims flat at the top level.
        extra_data = raw_extra.get("userinfo") or raw_extra

        def extract_org_unit(data):
            ents = data.get("edu_person_entitlements", [])
            for ent in ents:
                if "cid=ORG-" in ent:
                    return ent.split("cid=")[-1].split(":")[0]
            return None

        def extract_roles(data):
            """Extract roles from voperson_external_affiliation"""
            affiliations = data.get("voperson_external_affiliation", [])
            roles = []
            for affiliation in affiliations:
                # Parse "employee@rwth-aachen.de" -> "employee"
                if "@" in affiliation:
                    role = affiliation.split("@")[0]
                    roles.append(role)
            return roles

        # Extract names from NFDI claims in extra_data
        first_name = extra_data.get("given_name", "")
        last_name = extra_data.get("family_name", "")
        full_name = extra_data.get("name", "") or f"{first_name} {last_name}".strip()

        payload = {
            "id": sa.uid if sa else "",  # Use SocialAccount.uid (same as NFDI 'sub')
            "email": extra_data.get("email", ""),
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,
            "organization_id": None,
            "organization_unit_id": extract_org_unit(extra_data),
            "roles": extract_roles(extra_data),
            "access_token": token.token if token else None,
            "expires_at": token.expires_at.isoformat() if token and token.expires_at else None,
        }

        # validate against AuthProfileSerializer for consistent schema
        serializer = self.get_serializer(data=payload)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Generate JWT from authenticated user (social/session login)",
        responses={
            200: OpenApiResponse(
                description="JWT access and refresh tokens for authenticated user"
            ),
            401: OpenApiResponse(description="User not authenticated"),
        },
    )
    @action(detail=False, methods=["get"], url_path="jwt/social")
    def jwt_social(self, request):
        user = request.user
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
        )

    @extend_schema(
        summary="Logout the authenticated user",
        description="Logs out the user by clearing the Django session. Frontend should also clear any JWT tokens from local storage.",
        responses={
            200: OpenApiResponse(description="Logout successful"),
            401: OpenApiResponse(description="User not authenticated"),
        },
    )
    @action(detail=False, methods=["post"], url_path="logout")
    def logout(self, request):
        from django.contrib.auth import logout

        logout(request)
        return Response({"detail": "Successfully logged out."})

    @extend_schema(
        summary="Search for user profiles",
        description=(
            "Search for Person profiles by username, person_id, user_id, uuid, orcid, first_name, or last_name. "
            "At least one search parameter must be provided. Results respect privacy_level settings.\n"
            "- 'public': Visible to all authenticated users\n"
            "- 'private': Visible only to self and superusers\n\n"
            "Users always see their own profile regardless of privacy_level."
        ),
        parameters=[
            OpenApiParameter(
                name="username",
                location=OpenApiParameter.QUERY,
                required=False,
                description="Django User username (exact match, case-sensitive)",
                type=str,
            ),
            OpenApiParameter(
                name="person_id",
                location=OpenApiParameter.QUERY,
                required=False,
                description="Person model ID (integer)",
                type=int,
            ),
            OpenApiParameter(
                name="user_id",
                location=OpenApiParameter.QUERY,
                required=False,
                description="Django User model ID (integer)",
                type=int,
            ),
            OpenApiParameter(
                name="uuid",
                location=OpenApiParameter.QUERY,
                required=False,
                description="Person UUID",
                type=str,
            ),
            OpenApiParameter(
                name="orcid",
                location=OpenApiParameter.QUERY,
                required=False,
                description="ORCID identifier",
                type=str,
            ),
            OpenApiParameter(
                name="first_name",
                location=OpenApiParameter.QUERY,
                required=False,
                description="First name (case-insensitive partial match)",
                type=str,
            ),
            OpenApiParameter(
                name="last_name",
                location=OpenApiParameter.QUERY,
                required=False,
                description="Last name (case-insensitive partial match)",
                type=str,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=PersonProfileSerializer(many=True),
                description="List of matching Person profiles",
            ),
            400: OpenApiResponse(description="No search parameters provided"),
            401: OpenApiResponse(description="Authentication required"),
        },
    )
    @action(detail=False, methods=["get"], url_path="profile/search")
    def profile_search(self, request):
        """
        Search for Person profiles by various identifiers.
        Respects privacy_level settings.
        """
        user = request.user

        # Get search parameters
        username = request.query_params.get("username")
        person_id = request.query_params.get("person_id")
        user_id = request.query_params.get("user_id")
        uuid = request.query_params.get("uuid")
        orcid = request.query_params.get("orcid")
        first_name = request.query_params.get("first_name")
        last_name = request.query_params.get("last_name")

        # At least one parameter required
        if not any([username, person_id, user_id, uuid, orcid, first_name, last_name]):
            return Response(
                {
                    "detail": "At least one search parameter required: username, person_id, user_id, uuid, orcid, first_name, or last_name"
                },
                status=400,
            )

        # Build search query
        query = Q()

        if username:
            query |= Q(user__username=username)
        if person_id:
            try:
                query |= Q(id=int(person_id))
            except ValueError:
                pass
        if user_id:
            try:
                query |= Q(user__id=int(user_id))
            except ValueError:
                pass
        if uuid:
            query |= Q(uuid=uuid)
        if orcid:
            query |= Q(orcid=orcid)
        if first_name:
            query |= Q(first_name__icontains=first_name)
        if last_name:
            query |= Q(last_name__icontains=last_name)

        # Get Person queryset
        persons = cf.Person.objects.select_related("user").filter(query)

        # Apply privacy filtering
        if not user.is_superuser:
            # Authenticated users see public + internal; anonymous see only public
            privacy_filter = Q(privacy_level="public") | Q(privacy_level="internal")

            # Include user's own profile regardless of privacy_level
            try:
                own_person = cf.Person.objects.get(user=user)
                privacy_filter |= Q(id=own_person.id)
            except cf.Person.DoesNotExist:
                pass

            persons = persons.filter(privacy_filter)

        # Serialize and return
        serializer = PersonProfileSerializer(persons, many=True, context={"request": request})
        return Response(serializer.data)
