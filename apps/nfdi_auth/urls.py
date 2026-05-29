"""URL configuration for the nfdi_auth app."""

from django.urls import path

from nfdi_auth.views import CustomLoginView, profile_view

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="nfdi_login"),
    path("profile/", profile_view, name="nfdi_profile"),
]
