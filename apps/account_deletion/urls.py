"""
URL configuration for account_deletion app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AccountDeletionItemViewSet,
    AccountDeletionLogViewSet,
    AccountDeletionRequestViewSet,
)

app_name = 'account_deletion'

router = DefaultRouter()
router.register('requests', AccountDeletionRequestViewSet, basename='deletion-requests')
router.register('items', AccountDeletionItemViewSet, basename='deletion-items')
router.register('logs', AccountDeletionLogViewSet, basename='deletion-logs')

urlpatterns = [
    path('', include(router.urls)),
]
