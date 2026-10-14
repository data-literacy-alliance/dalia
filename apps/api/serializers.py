# api/serializers.py
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .utils.jwt import custom_jwt_payload

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        extra = custom_jwt_payload(self.user)
        data.update(extra)
        return data


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name"]


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "codename", "name"]


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User accounts, including staff roles."""

    groups = GroupSerializer(many=True, read_only=True)
    user_permissions = PermissionSerializer(many=True, read_only=True)
    effective_permissions = serializers.SerializerMethodField()
    is_curator = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "is_staff",
            "is_superuser",
            "is_curator",
            "groups",
            "user_permissions",
            "effective_permissions",
        ]
        read_only_fields = ["is_superuser"]  # no superuser via API for safety

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_effective_permissions(self, obj):
        # Get all permission codenames the user effectively has
        return sorted(set(obj.get_all_permissions()))

    @extend_schema_field(serializers.BooleanField())
    def get_is_curator(self, obj):
        return obj.is_superuser or obj.groups.filter(name="Curators").exists()


class AuthProfileSerializer(serializers.Serializer):
    id = serializers.CharField(allow_blank=True)  # NFDI sub field
    email = serializers.EmailField(allow_blank=True)
    first_name = serializers.CharField(allow_blank=True)
    last_name = serializers.CharField(allow_blank=True)
    full_name = serializers.CharField(allow_blank=True)
    organization_id = serializers.CharField(allow_null=True, allow_blank=True)
    organization_unit_id = serializers.CharField(allow_null=True, allow_blank=True)
    roles = serializers.ListField(child=serializers.CharField())
    access_token = serializers.CharField(allow_null=True, allow_blank=True)
    expires_at = serializers.DateTimeField(allow_null=True)


class PersonProfileSerializer(serializers.Serializer):
    """
    Serializer for Person profile search results.
    Returns Person model fields respecting privacy_level.
    """

    # Person model fields
    id = serializers.IntegerField(read_only=True)
    uuid = serializers.UUIDField(read_only=True)

    # Related User info (for context)
    user_id = serializers.IntegerField(source="user.id", read_only=True, allow_null=True)
    username = serializers.CharField(source="user.username", read_only=True, allow_null=True)

    # Person profile fields
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    full_name = serializers.SerializerMethodField()
    orcid = serializers.SerializerMethodField()
    homepage = serializers.SerializerMethodField()
    uri = serializers.URLField()

    # Privacy and preferences
    privacy_level = serializers.CharField()
    email_notifications = serializers.BooleanField()
    sync_name_from_provider = serializers.BooleanField()
    is_active = serializers.BooleanField()

    # Timestamps
    created = serializers.DateTimeField(read_only=True)
    modified = serializers.DateTimeField(read_only=True)

    @extend_schema_field(serializers.CharField())
    def get_full_name(self, obj):
        """Return the full name from Person model."""
        return obj.full_name

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_orcid(self, obj):
        if self._is_visible(obj):
            return obj.orcid
        return None

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_homepage(self, obj):
        if self._is_visible(obj):
            return obj.homepage
        return None

    def _is_visible(self, obj):
        """Return True if sensitive fields should be shown."""
        if obj.privacy_level == "public":
            return True
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            # Internal profiles expose orcid/homepage to any logged-in user
            if obj.privacy_level == "internal":
                return True
            try:
                from curation.models import Person

                own = Person.objects.get(user=request.user)
                return own.pk == obj.pk
            except Person.DoesNotExist:
                pass
        return False
