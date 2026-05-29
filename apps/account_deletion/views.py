"""
API views for account deletion operations.
"""

from django.contrib.auth import get_user_model
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import AccountDeletionItem, AccountDeletionLog, AccountDeletionRequest
from .serializers import (
    AccountDeletionCancelSerializer,
    AccountDeletionConfirmSerializer,
    AccountDeletionItemSerializer,
    AccountDeletionLogSerializer,
    AccountDeletionRequestCreateSerializer,
    AccountDeletionRequestSerializer,
    AccountDeletionStatusSerializer,
)
from .services import AccountDeletionService

User = get_user_model()


class IsAdminOrSelf(permissions.BasePermission):
    """
    Allow access to own deletion requests or if user is admin/superuser.
    """
    def has_object_permission(self, request, view, obj):
        return (
            request.user.is_superuser or
            request.user.is_staff or
            obj.user == request.user
        )


@extend_schema(tags=["Account Management • GDPR Deletion"])
class AccountDeletionRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managing account deletion requests.
    """
    queryset = AccountDeletionRequest.objects.all().order_by('-initiated_at')
    serializer_class = AccountDeletionRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrSelf]
    lookup_field = 'uuid'

    def get_queryset(self):
        """
        Filter queryset based on user permissions.
        Regular users see only their own requests.
        Admins see all requests.
        """
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return self.queryset
        return self.queryset.filter(user=user)

    @extend_schema(
        summary="Create deletion request",
        request=AccountDeletionRequestCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=AccountDeletionRequestSerializer,
                description="Deletion request created successfully"
            ),
            400: OpenApiResponse(description="User already has an active deletion request"),
            403: OpenApiResponse(description="Not permitted to create request for this user"),
        },
        examples=[
            OpenApiExample(
                "Self-deletion request",
                value={},
                request_only=True,
                description="Creates deletion request for the authenticated user"
            ),
            OpenApiExample(
                "Admin-initiated deletion",
                value={"user_id": 23},
                request_only=True,
                description="Admin creates deletion request for user ID 23"
            ),
        ]
    )
    @action(detail=False, methods=['post'], url_path='create')
    def create_request(self, request):
        """Create a new deletion request."""
        serializer = AccountDeletionRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data.get('user_id')

        if user_id:
            if not (request.user.is_superuser or request.user.is_staff):
                return Response(
                    {"detail": "Only admins can create deletion requests for other users"},
                    status=status.HTTP_403_FORBIDDEN
                )
            try:
                target_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(
                    {"detail": f"User with ID {user_id} not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            initiated_by = request.user
        else:
            target_user = request.user
            initiated_by = None

        ip_address = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        try:
            deletion_request = AccountDeletionService.create_deletion_request(
                user=target_user,
                initiated_by=initiated_by,
                ip_address=ip_address,
                user_agent=user_agent
            )

            AccountDeletionService.send_confirmation_email(deletion_request)

            response_serializer = AccountDeletionRequestSerializer(
                deletion_request,
                context={'request': request}
            )

            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )

        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        summary="Confirm deletion (public endpoint)",
        parameters=[
            OpenApiParameter(
                name="token",
                location=OpenApiParameter.PATH,
                required=True,
                description="Confirmation token UUID from email",
                type=str
            )
        ],
        responses={
            200: OpenApiResponse(
                response=AccountDeletionConfirmSerializer,
                description="Deletion confirmed successfully"
            ),
            400: OpenApiResponse(description="Invalid or expired token"),
        }
    )
    @action(
        detail=False,
        methods=['post'],
        url_path='confirm/(?P<token>[0-9a-f-]+)',
        permission_classes=[permissions.AllowAny]
    )
    def confirm(self, request, token=None):
        """Confirm deletion using email token."""
        ip_address = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        try:
            deletion_request = AccountDeletionService.confirm_deletion(
                confirmation_token=token,
                ip_address=ip_address,
                user_agent=user_agent
            )

            response_data = {
                'status': 'confirmed',
                'message': 'Deletion confirmed. You have 30 days to cancel before permanent deletion.',
                'deletion_scheduled_at': deletion_request.deletion_scheduled_at,
                'cancellation_url': request.build_absolute_uri(
                    f'/api/account/delete-cancel/{token}/'
                ),
                'days_remaining': 30,
            }

            serializer = AccountDeletionConfirmSerializer(response_data)
            return Response(serializer.data)

        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        summary="Cancel deletion (public endpoint)",
        parameters=[
            OpenApiParameter(
                name="token",
                location=OpenApiParameter.PATH,
                required=True,
                description="Confirmation token UUID from email",
                type=str
            )
        ],
        responses={
            200: OpenApiResponse(
                response=AccountDeletionCancelSerializer,
                description="Deletion cancelled successfully"
            ),
            400: OpenApiResponse(description="Cannot cancel this request"),
        }
    )
    @action(
        detail=False,
        methods=['post'],
        url_path='cancel/(?P<token>[0-9a-f-]+)',
        permission_classes=[permissions.AllowAny]
    )
    def cancel(self, request, token=None):
        """Cancel deletion using email token."""
        try:
            deletion_request = AccountDeletionRequest.objects.get(
                confirmation_token=token
            )
        except AccountDeletionRequest.DoesNotExist:
            return Response(
                {"detail": "Invalid cancellation token"},
                status=status.HTTP_404_NOT_FOUND
            )

        if not deletion_request.can_be_cancelled:
            return Response(
                {"detail": f"Cannot cancel request in status: {deletion_request.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        ip_address = self._get_client_ip(request)

        try:
            cancelled_request = AccountDeletionService.cancel_deletion(
                deletion_request=deletion_request,
                cancelled_by=deletion_request.user,
                reason="Cancelled by user via email link",
                ip_address=ip_address
            )

            response_data = {
                'status': 'cancelled',
                'message': 'Deletion request cancelled successfully.',
                'cancelled_at': cancelled_request.cancelled_at,
            }

            serializer = AccountDeletionCancelSerializer(response_data)
            return Response(serializer.data)

        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        summary="Check deletion status (public endpoint)",
        parameters=[
            OpenApiParameter(
                name="token",
                location=OpenApiParameter.PATH,
                required=True,
                description="Confirmation token UUID from email",
                type=str
            )
        ],
        responses={
            200: OpenApiResponse(
                response=AccountDeletionStatusSerializer,
                description="Deletion status"
            ),
            404: OpenApiResponse(description="Request not found"),
        }
    )
    @action(
        detail=False,
        methods=['get'],
        url_path='status/(?P<token>[0-9a-f-]+)',
        permission_classes=[permissions.AllowAny]
    )
    def check_status(self, request, token=None):
        """Check status of deletion request."""
        try:
            deletion_request = AccountDeletionRequest.objects.get(
                confirmation_token=token
            )
        except AccountDeletionRequest.DoesNotExist:
            return Response(
                {"detail": "Request not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        response_data = {
            'status': deletion_request.status,
            'days_remaining': deletion_request.days_until_deletion,
            'deletion_scheduled_at': deletion_request.deletion_scheduled_at,
            'can_cancel': deletion_request.can_be_cancelled,
            'initiated_at': deletion_request.initiated_at,
            'confirmed_at': deletion_request.confirmed_at,
        }

        serializer = AccountDeletionStatusSerializer(response_data)
        return Response(serializer.data)

    @extend_schema(
        summary="List my deletion requests",
        responses={
            200: OpenApiResponse(
                response=AccountDeletionRequestSerializer(many=True),
                description="List of deletion requests"
            ),
        }
    )
    @action(detail=False, methods=['get'], url_path='my-requests')
    def my_requests(self, request):
        """List deletion requests for current user."""
        requests = AccountDeletionRequest.objects.filter(
            user=request.user
        ).order_by('-initiated_at')

        serializer = self.get_serializer(requests, many=True)
        return Response(serializer.data)

    def _get_client_ip(self, request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@extend_schema(tags=["Account Management • GDPR Deletion"])
class AccountDeletionItemViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing deletion items (admin only).
    """
    queryset = AccountDeletionItem.objects.all().order_by('app_label', 'model_name')
    serializer_class = AccountDeletionItemSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'uuid'

    def get_queryset(self):
        qs = super().get_queryset()
        request_uuid = self.request.query_params.get('deletion_request')
        if request_uuid:
            qs = qs.filter(deletion_request__uuid=request_uuid)
        return qs


@extend_schema(tags=["Account Management • GDPR Deletion"])
class AccountDeletionLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing audit logs (admin only).
    """
    queryset = AccountDeletionLog.objects.all().order_by('-timestamp')
    serializer_class = AccountDeletionLogSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'uuid'

    def get_queryset(self):
        qs = super().get_queryset()
        request_uuid = self.request.query_params.get('deletion_request')
        if request_uuid:
            qs = qs.filter(deletion_request__uuid=request_uuid)
        return qs
