from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions
from rest_framework.generics import RetrieveAPIView

from pages.models import Page
from pages.serializers import PageSerializer


@extend_schema(
    summary="Retrieve a managed page by slug and language",
    parameters=[
        OpenApiParameter(
            "slug", str, OpenApiParameter.PATH, description="Page slug, e.g. privacy-policy"
        ),
        OpenApiParameter("lang", str, OpenApiParameter.PATH, description="Language code: de or en"),
    ],
    responses={
        200: OpenApiResponse(response=PageSerializer, description="Page content returned"),
        404: OpenApiResponse(description="Page not found for this slug/language combination"),
    },
)
class PageDetailView(RetrieveAPIView):
    serializer_class = PageSerializer
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        return get_object_or_404(
            Page,
            slug=self.kwargs["slug"],
            language=self.kwargs["lang"],
        )
