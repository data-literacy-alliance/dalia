"""
URL configuration for app 'recommendation'.

Provides endpoints for fetching learning resource recommendations.
"""

from django.urls import path

from . import views

app_name = "recommendation"

urlpatterns = [
    path(
        "v1/item/<uuid:material_id>/recommendations",
        views.MaterialSuggestionsView.as_view(),
        name="material_recommendations",
    ),
]
