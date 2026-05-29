# api/urls.py
from account_deletion.views import (
    AccountDeletionItemViewSet,
    AccountDeletionLogViewSet,
    AccountDeletionRequestViewSet,
)
from django.http import JsonResponse
from django.urls import include, path
from rest_framework.authtoken import views as drf_auth_views
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import CustomTokenObtainPairSerializer
from .views import AuthViewSet, UserViewSet
from .views_curation import (
    BookmarkViewSet,
    CommunityMembershipViewSet,
    CommunityViewSet,
    DisciplineViewSet,
    EditLogViewSet,
    FileFormatViewSet,
    LanguageViewSet,
    LearningResourceTypeViewSet,
    LicenseViewSet,
    LikeViewSet,
    MediaTypeViewSet,
    OrganizationViewSet,
    PersonViewSet,
    ProficiencyLevelViewSet,
    RelationTypeCategoryViewSet,
    RelationTypeViewSet,
    ResourceCommunityRelationViewSet,
    ResourceConsentViewSet,
    ResourceContentViewSet,
    ResourceLinkViewSet,
    ResourcePublishingConsentViewSet,
    ResourceRelatedItemViewSet,
    ResourceViewSet,
    ReviewQuestionViewSet,
    ReviewViewSet,
    TargetGroupViewSet,
    ViewEventViewSet,
)
from .views_suggest import (
    CurationSuggestCommunitiesView,
    CurationSuggestDisciplinesView,
    CurationSuggestLanguagesView,
    CurationSuggestLearningResourceTypesView,
    CurationSuggestLicensesView,
    CurationSuggestMediaTypesView,
    CurationSuggestProficiencyLevelsView,
    CurationSuggestRelationTypesView,
    CurationSuggestTargetGroupsView,
)


class CustomTokenView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


router = DefaultRouter()

# User / auth
router.register('users', UserViewSet, basename='user')
router.register('auth', AuthViewSet, basename='auth')

# Curation vocab + resources
router.register('curation/communities', CommunityViewSet, basename='curation-communities')
router.register('curation/disciplines', DisciplineViewSet, basename='curation-disciplines')
router.register('curation/file-formats', FileFormatViewSet, basename='curation-fileformats')
router.register('curation/learning-resource-types', LearningResourceTypeViewSet, basename='curation-lrtypes')
router.register('curation/licenses', LicenseViewSet, basename='curation-licenses')
router.register('curation/media-types', MediaTypeViewSet, basename='curation-mediatypes')
router.register('curation/languages', LanguageViewSet, basename='curation-languages')
router.register('curation/organizations', OrganizationViewSet, basename='curation-organizations')
router.register('curation/persons', PersonViewSet, basename='curation-persons')
router.register('curation/proficiency-levels', ProficiencyLevelViewSet, basename='curation-proficiency')
router.register('curation/target-groups', TargetGroupViewSet, basename='curation-targetgroups')

# Main resource endpoints (UUID-based)
router.register('curation/resources', ResourceViewSet, basename='curation-resources')
router.register('curation/resource-contents', ResourceContentViewSet, basename='curation-resourcecontents')

# Community management
router.register('curation/memberships', CommunityMembershipViewSet, basename='curation-memberships')

# User interactions
router.register('curation/bookmarks', BookmarkViewSet, basename='curation-bookmarks')
router.register('curation/likes', LikeViewSet, basename='curation-likes')

# Analytics (admin only)
router.register('curation/view-events', ViewEventViewSet, basename='curation-viewevents')
router.register('curation/edit-logs', EditLogViewSet, basename='curation-editlogs')

# Review system
router.register('curation/reviews', ReviewViewSet, basename='curation-reviews')
router.register('curation/review-questions', ReviewQuestionViewSet, basename='curation-reviewquestions')

# Legal compliance
router.register('curation/consents', ResourceConsentViewSet, basename='curation-consents')
router.register('curation/publishing-consents', ResourcePublishingConsentViewSet, basename='curation-publishingconsents')

# Relation types
router.register('curation/relation-type-categories', RelationTypeCategoryViewSet, basename='curation-relationtypecategories')
router.register('curation/relation-types', RelationTypeViewSet, basename='curation-relationtypes')

# Resource relations
router.register('curation/resource-links', ResourceLinkViewSet, basename='curation-resourcelinks')
router.register('curation/community-relations', ResourceCommunityRelationViewSet, basename='curation-communityrelations')
router.register('curation/related-items', ResourceRelatedItemViewSet, basename='curation-relateditems')

# Account deletion (GDPR)
router.register('account/deletion-requests', AccountDeletionRequestViewSet, basename='account-deletion-requests')
router.register('account/deletion-items', AccountDeletionItemViewSet, basename='account-deletion-items')
router.register('account/deletion-logs', AccountDeletionLogViewSet, basename='account-deletion-logs')


urlpatterns = [
    # Auth token endpoint (for login via API using session/password)
    path('auth/token/', drf_auth_views.obtain_auth_token, name='api_token_auth'),

    # Curation suggest/autocomplete endpoints (search app disabled — returns 503)
    path('v1/curation/suggest/communities/', CurationSuggestCommunitiesView.as_view(), name='suggest-communities'),
    path('v1/curation/suggest/learning-resource-types/', CurationSuggestLearningResourceTypesView.as_view(), name='suggest-lrtypes'),
    path('v1/curation/suggest/languages/', CurationSuggestLanguagesView.as_view(), name='suggest-languages'),
    path('v1/curation/suggest/disciplines/', CurationSuggestDisciplinesView.as_view(), name='suggest-disciplines'),
    path('v1/curation/suggest/licenses/', CurationSuggestLicensesView.as_view(), name='suggest-licenses'),
    path('v1/curation/suggest/proficiency-levels/', CurationSuggestProficiencyLevelsView.as_view(), name='suggest-proficiency'),
    path('v1/curation/suggest/target-groups/', CurationSuggestTargetGroupsView.as_view(), name='suggest-targetgroups'),
    path('v1/curation/suggest/media-types/', CurationSuggestMediaTypesView.as_view(), name='suggest-mediatypes'),
    path('v1/curation/suggest/relation-types/', CurationSuggestRelationTypesView.as_view(), name='suggest-relationtypes'),

    # Ping test route
    path('ping/', lambda request: JsonResponse({'ok': True})),

    path('', include(router.urls)),
]
