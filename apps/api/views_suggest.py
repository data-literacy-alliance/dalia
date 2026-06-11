"""REST API views for curation autocomplete/suggest endpoints."""

import dataclasses

from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from search.api_models.api_models import (
    CurationSuggestLicensesRequest,
    CurationSuggestSearchRequest,
)
from search.suggest.communities import get_communities_suggestions
from search.suggest.disciplines import get_disciplines_suggestions
from search.suggest.languages import get_languages_suggestions
from search.suggest.learning_resource_types import get_learning_resource_types_suggestions
from search.suggest.licenses import get_licenses_suggestions
from search.suggest.media_types import get_media_types_suggestions
from search.suggest.proficiency_levels import get_proficiency_levels_suggestions
from search.suggest.relation_types import get_relation_types_suggestions
from search.suggest.target_groups import get_target_groups_suggestions


def _parse_params(request: Request):
    q = request.query_params.get("q", "")
    limit = int(request.query_params.get("limit", 10))
    offset = int(request.query_params.get("offset", 0))
    return q, limit, offset


class CurationSuggestCommunitiesView(APIView):
    """GET /v1/curation/suggest/communities/?q=<search_term>&limit=10&offset=0"""

    permission_classes = [AllowAny]

    def get(self, request: Request):
        q, limit, offset = _parse_params(request)
        result = get_communities_suggestions(
            CurationSuggestSearchRequest(q=q, limit=limit, offset=offset)
        )
        return Response(dataclasses.asdict(result))


class CurationSuggestLearningResourceTypesView(APIView):
    """GET /v1/curation/suggest/learning-resource-types/?q=<search_term>"""

    permission_classes = [AllowAny]

    def get(self, request: Request):
        q, limit, offset = _parse_params(request)
        result = get_learning_resource_types_suggestions(
            CurationSuggestSearchRequest(q=q, limit=limit, offset=offset)
        )
        return Response([dataclasses.asdict(item) for item in result])


class CurationSuggestLanguagesView(APIView):
    """GET /v1/curation/suggest/languages/?q=<search_term>&limit=10&offset=0"""

    permission_classes = [AllowAny]

    def get(self, request: Request):
        q, limit, offset = _parse_params(request)
        result = get_languages_suggestions(
            CurationSuggestSearchRequest(q=q, limit=limit, offset=offset)
        )
        return Response(dataclasses.asdict(result))


class CurationSuggestDisciplinesView(APIView):
    """GET /v1/curation/suggest/disciplines/?q=<search_term>"""

    permission_classes = [AllowAny]

    def get(self, request: Request):
        q, limit, offset = _parse_params(request)
        result = get_disciplines_suggestions(
            CurationSuggestSearchRequest(q=q, limit=limit, offset=offset)
        )
        return Response([dataclasses.asdict(item) for item in result])


class CurationSuggestLicensesView(APIView):
    """GET /v1/curation/suggest/licenses/?q=<search_term>&filter=all"""

    permission_classes = [AllowAny]

    def get(self, request: Request):
        q, limit, offset = _parse_params(request)
        license_filter = request.query_params.get("filter", "all")
        result = get_licenses_suggestions(
            CurationSuggestLicensesRequest(q=q, limit=limit, offset=offset, filter=license_filter)
        )
        return Response(dataclasses.asdict(result))


class CurationSuggestProficiencyLevelsView(APIView):
    """GET /v1/curation/suggest/proficiency-levels/?q=<search_term>"""

    permission_classes = [AllowAny]

    def get(self, request: Request):
        q, limit, offset = _parse_params(request)
        result = get_proficiency_levels_suggestions(
            CurationSuggestSearchRequest(q=q, limit=limit, offset=offset)
        )
        return Response([dataclasses.asdict(item) for item in result])


class CurationSuggestTargetGroupsView(APIView):
    """GET /v1/curation/suggest/target-groups/?q=<search_term>"""

    permission_classes = [AllowAny]

    def get(self, request: Request):
        q, limit, offset = _parse_params(request)
        result = get_target_groups_suggestions(
            CurationSuggestSearchRequest(q=q, limit=limit, offset=offset)
        )
        return Response([dataclasses.asdict(item) for item in result])


class CurationSuggestMediaTypesView(APIView):
    """GET /v1/curation/suggest/media-types/?q=<search_term>"""

    permission_classes = [AllowAny]

    def get(self, request: Request):
        q, limit, offset = _parse_params(request)
        result = get_media_types_suggestions(
            CurationSuggestSearchRequest(q=q, limit=limit, offset=offset)
        )
        return Response([dataclasses.asdict(item) for item in result])


class CurationSuggestRelationTypesView(APIView):
    """GET /v1/curation/suggest/relation-types/?q=<search_term>"""

    permission_classes = [AllowAny]

    def get(self, request: Request):
        q, limit, offset = _parse_params(request)
        result = get_relation_types_suggestions(
            CurationSuggestSearchRequest(q=q, limit=limit, offset=offset)
        )
        return Response([dataclasses.asdict(item) for item in result])
