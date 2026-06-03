"""
Core base views: health check and admin logout.
"""

from django.contrib.auth import logout
from django.core.cache import cache
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint for monitoring (public, no authentication required)."""
    # Test Redis cache connectivity
    cache_status = "unavailable"
    try:
        cache.set("health_check", "ok", timeout=10)
        if cache.get("health_check") == "ok":
            cache_status = "connected"
        cache.delete("health_check")
    except Exception as e:
        cache_status = f"error: {str(e)}"

    return Response(
        {
            "status": "healthy",
            "version": "1.0.0",
            "cache": cache_status,
        }
    )


@csrf_exempt
def admin_logout(request):
    """
    Custom logout view for admin panel.
    Handles both GET and POST requests without CSRF verification.
    """
    logout(request)
    return redirect("/admin/login/")
