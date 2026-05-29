"""
Serializers for recommendation API.

Uses dataclass serializers for suggested content responses.
"""

from rest_framework_dataclasses.serializers import DataclassSerializer

from .api_models import api_models


class SuggestedContentSerializer(DataclassSerializer):
    """Serializer for suggested content responses."""

    class Meta:
        dataclass = api_models.SuggestedContents
