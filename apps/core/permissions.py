"""
DRF permission classes for Work Track Pro.

This module implements role-based access control (RBAC) and team-scoped
authorization for the REST API.
"""

from rest_framework.permissions import BasePermission


class IsAdminOrReadOnly(BasePermission):
    """
    Permission class that allows:
    - Read access for all authenticated users
    - Write access only for users in the 'Admin' group

    Used for configuration and master data endpoints where employees
    should be able to view but not modify.
    """

    def has_permission(self, request, view):
        # Read permissions are allowed for any authenticated user
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return request.user and request.user.is_authenticated

        # Write permissions only for Admin group members
        return (
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(name="Admin").exists()
        )


class IsSupervisorOrAbove(BasePermission):
    """
    Permission class that allows access only to users in Supervisor,
    Manager, HR, or Admin groups.

    Used for endpoints that require supervisory or management level access,
    such as approving leave requests or viewing team reports.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.groups.filter(
                name__in=["Supervisor", "Manager", "HR", "Admin"]
            ).exists()
        )


class IsOwnerOrSupervisor(BasePermission):
    """
    Object-level permission that allows:
    - Owners (employees) to access their own data
    - Supervisors, Managers, HR, and Admins to access any data within their scope

    Note: This provides basic object-level access. Team-scoped filtering
    should be implemented in ViewSet.get_queryset() to restrict supervisors
    to their own team's data.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        # Admin always has access
        if user.groups.filter(name="Admin").exists():
            return True

        # Check if user is the owner (for objects with a 'user' FK)
        if hasattr(obj, "user") and obj.user == user:
            return True

        # Check if user is the employee instance themselves
        if hasattr(obj, "employee") and hasattr(user, "employee"):
            if obj == user.employee or (hasattr(obj, "employee") and obj.employee == user.employee):
                return True

        # Supervisors, Managers, HR can access (ViewSet should filter by team)
        if user.groups.filter(name__in=["Supervisor", "Manager", "HR"]).exists():
            return True

        return False


class IsTeamScoped(BasePermission):
    """
    Permission class that restricts access to objects belonging to the user's team(s).

    - Employees: only their own data
    - Supervisors: their own team's data
    - Managers: all teams
    - HR: all employees
    - Admin: everything

    This is an object-level permission. ViewSets MUST also implement queryset
    filtering in get_queryset() for proper team scoping on list views.
    """

    def get_user_team_ids(self, user):
        """
        Return team IDs the user is authorized to access.
        Returns None for unrestricted access (Manager, Admin, HR).
        Returns [] if user has no team association.
        """
        if not user or not user.is_authenticated:
            return []

        # Superuser and Admin: unrestricted
        if user.is_superuser or user.groups.filter(name="Admin").exists():
            return None

        # Manager and HR: unrestricted
        if user.groups.filter(name__in=["Manager", "HR"]).exists():
            return None

        # Supervisor: their own team only
        employee = getattr(user, "employee", None)
        if not employee:
            return []

        if user.groups.filter(name="Supervisor").exists():
            return [employee.team_id] if employee.team_id else []

        # Regular employee: no team-based access (only own records)
        return []

    def has_permission(self, request, view):
        """
        Always return True for authenticated users.
        Actual filtering happens in has_object_permission and ViewSet.get_queryset().
        """
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """
        Check if user has access to this specific object based on team membership.
        """
        user = request.user

        if not user or not user.is_authenticated:
            return False

        team_ids = self.get_user_team_ids(user)

        # None = unrestricted access (Manager, Admin, HR)
        if team_ids is None:
            return True

        # Check if object belongs to user's team
        if hasattr(obj, "team_id"):
            return obj.team_id in team_ids

        if hasattr(obj, "team") and hasattr(obj.team, "id"):
            return obj.team.id in team_ids

        # For objects related to employees (e.g., Leave, TimeEntry)
        if hasattr(obj, "employee"):
            employee = obj.employee
            # Allow owner access (employee viewing their own leave)
            if hasattr(user, "employee") and employee == user.employee:
                return True
            # Check team membership
            if hasattr(employee, "team_id"):
                return employee.team_id in team_ids
            if hasattr(employee, "team") and hasattr(employee.team, "id"):
                return employee.team.id in team_ids

        # If object has a user FK (direct ownership)
        if hasattr(obj, "user") and obj.user == user:
            return True

        # Default deny
        return False
