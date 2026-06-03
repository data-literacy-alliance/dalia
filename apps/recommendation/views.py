"""
Recommendation API views.

This module provides recommendation endpoints for learning resources.

Note: This app currently depends on the legacy dalia app which will be
migrated in Phase 3 of the project migration. The imports below reference
dalia_project.dalia which needs to be refactored.
"""

from uuid import UUID

from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from . import serializers
from .materials.suggested_content import get_suggested_contents


# endpoint /items/<uuid:material_id>/recommendations
class MaterialSuggestionsView(APIView):
    """
    API view for fetching recommended learning resources based on a given material.

    Recommendations are cached for 5 minutes to improve performance.
    """

    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def get(self, request: Request, material_id: UUID):
        """
        Get recommendations for a learning resource.

        Args:
            request: The HTTP request
            material_id: UUID of the learning resource

        Returns:
            Response with suggested contents or 404 if no suggestions found
        """
        # Try to get from cache first
        cache_key = f"recommendations_{material_id}"
        cached_result = cache.get(cache_key)

        if cached_result:
            return Response(cached_result)

        suggested_contents = get_suggested_contents(material_id)
        if len(suggested_contents.results) == 0:
            return Response({"messages": "No suggestions found"}, status=status.HTTP_404_NOT_FOUND)

        result = serializers.SuggestedContentSerializer(suggested_contents)

        # Store in cache
        cache.set(cache_key, result.data, 60 * 5)  # 5 minutes

        return Response(result.data)
