"""
Django REST Framework serializers for search and curation suggest endpoints.

These serializers use DataclassSerializer to automatically serialize/deserialize
dataclass-based API models defined in api_models/api_models.py.
"""
from rest_framework_dataclasses.serializers import DataclassSerializer

import search.api_models.api_models as api_models


class BasicSearchFilterSerializer(DataclassSerializer):
    class Meta:
        dataclass = api_models.BasicSearchFilter


class CommunitySerializer(DataclassSerializer):
    class Meta:
        dataclass = api_models.Community


class ItemSerializer(DataclassSerializer):
    class Meta:
        dataclass = api_models.Resource


class ItemSearchResultSerializer(DataclassSerializer):
    class Meta:
        dataclass = api_models.ItemSearchResult


class ItemSearchRequestSerializer(DataclassSerializer):
    class Meta:
        dataclass = api_models.ItemSearchRequest


class CurationSuggestSearchRequestSerializer(DataclassSerializer):
    class Meta:
        dataclass = api_models.CurationSuggestSearchRequest


class LabelValueItemSerializer(DataclassSerializer):
    class Meta:
        dataclass = api_models.LabelValueItem


class CurationSuggestPaginatedResultSerializer(DataclassSerializer):
    class Meta:
        dataclass = api_models.CurationSuggestPaginatedResult


class CurationSuggestDisciplinesResultItemSerializer(DataclassSerializer):
    class Meta:
        dataclass = api_models.CurationSuggestDisciplinesResultItem


class CurationSuggestLicensesRequestSerializer(DataclassSerializer):
    class Meta:
        dataclass = api_models.CurationSuggestLicensesRequest


class CurationSuggestLicensesResultSerializer(DataclassSerializer):
    class Meta:
        dataclass = api_models.CurationSuggestLicensesResult
