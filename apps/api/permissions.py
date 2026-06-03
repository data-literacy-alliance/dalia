"""
Custom permissions for API endpoints.

Security Model
--------------

The API implements a layered security model:

1. Public Read Access (AllowAny for read operations):
   Vocabularies, Communities, Resources, published ResourceContent, public profiles.

2. Authenticated Write Access (IsAuthenticated):
   Creating/updating vocabularies, ResourceContent, bookmarks, likes, reviews, memberships.

3. Admin-Only Access (IsAdminUser):
   ViewEvent analytics, EditLog history, system-level operations.

4. Dynamic Permissions:
   ResourceContentViewSet uses get_permissions() for action-based permissions.
"""

from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    Read operations are allowed for anyone.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner
        return obj.owner == request.user or obj.user == request.user


class IsCuratorOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow curators or admins to edit.
    Read operations are allowed for anyone.
    """

    def has_permission(self, request, view):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions require curator role or admin
        if not request.user.is_authenticated:
            return False

        return request.user.is_superuser or request.user.groups.filter(name="Curators").exists()


class IsAdminOrOwner(permissions.BasePermission):
    """
    Custom permission to allow admins full access,
    and owners to access their own objects.
    """

    def has_object_permission(self, request, view, obj):
        # Admins can do anything
        if request.user.is_superuser:
            return True

        # Check various owner fields
        if hasattr(obj, "owner") and obj.owner == request.user:
            return True
        if hasattr(obj, "user") and obj.user == request.user:
            return True
        if hasattr(obj, "created_by") and obj.created_by == request.user:
            return True

        return False
