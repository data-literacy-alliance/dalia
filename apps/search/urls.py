"""
URL configuration for search and metadata retrieval endpoints.

These endpoints provide public access to search functionality and resource metadata.
"""

from django.urls import path

from . import views

app_name = "search"

urlpatterns = [
    # Search filters
    path(
        "v1/basic-search-filters/",
        views.BasicSearchFiltersView.as_view(),
        name="basic_search_filters",
    ),
    # Item endpoints
    path(
        "v1/items/<uuid:resource_id>/view/",
        views.ItemViewEventView.as_view(),
        name="item_view_event",
    ),
    path("v1/items/<uuid:resource_id>/", views.ItemView.as_view(), name="item_detail"),
    path("v1/items/", views.ItemSearchView.as_view(), name="item_search"),
    # Curation suggest endpoints
    path(
        "v1/curation/suggest/communities/",
        views.CurationSuggestCommunitiesView.as_view(),
        name="curation_suggest_communities",
    ),
    # Community endpoints
    path(
        "v1/communities/<uuid:community_id>/",
        views.CommunityView.as_view(),
        name="community_detail",
    ),
    path(
        "v1/communities/<uuid:community_id>/items/",
        views.CommunityItemsView.as_view(),
        name="community_items",
    ),
]
