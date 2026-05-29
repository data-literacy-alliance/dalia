"""
Core URL patterns.
"""

from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from . import views

urlpatterns = [
    path("health/", views.health_check, name="health-check"),
    path("auth/token/", obtain_auth_token, name="api-token-auth"),
]
