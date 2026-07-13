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
    # Item interaction endpoints (authentication required)
    path(
        "v1/items/<uuid:resource_id>/bookmark/",
        views.ItemBookmarkView.as_view(),
        name="item_bookmark",
    ),
    path(
        "v1/items/<uuid:resource_id>/like/",
        views.ItemLikeView.as_view(),
        name="item_like",
    ),
    path(
        "v1/items/<uuid:resource_id>/interactions/",
        views.ItemInteractionsView.as_view(),
        name="item_interactions",
    ),
    # Item view tracking (public)
    path(
        "v1/items/<uuid:resource_id>/view/",
        views.ItemViewEventView.as_view(),
        name="item_view_event",
    ),
    path("v1/items/<uuid:resource_id>/", views.ItemView.as_view(), name="item_detail"),
    path("v1/items/", views.ItemSearchView.as_view(), name="item_search"),
    # User activity endpoints (authentication required)
    path(
        "v1/activities/bookmarks/",
        views.UserBookmarksListView.as_view(),
        name="user_bookmarks",
    ),
    path(
        "v1/activities/likes/",
        views.UserLikesListView.as_view(),
        name="user_likes",
    ),
    # Curation suggest endpoints
    path(
        "v1/curation/suggest/communities/",
        views.CurationSuggestCommunitiesView.as_view(),
        name="curation_suggest_communities",
    ),
    # Community endpoints
    path(
        "v1/communities/<uuid:community_id>/view/",
        views.CommunityViewEventView.as_view(),
        name="community_view_event",
    ),
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
