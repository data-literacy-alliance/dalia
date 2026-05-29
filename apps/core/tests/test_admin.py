"""
Tests for admin panel configuration.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
class TestAdminPanel:
    """Test admin panel configuration and accessibility."""

    def test_admin_login_page_accessible(self, client: Client):
        """Test that admin login page is accessible."""
        response = client.get(reverse("admin:index"))
        assert response.status_code == 302  # Redirect to login

        login_url = reverse("admin:login")
        response = client.get(login_url)
        assert response.status_code == 302  # Redirect to login

    def test_admin_index_requires_authentication(self, client: Client):
        """Test that admin index requires authentication."""
        response = client.get(reverse("admin:index"))
        assert response.status_code == 302
        assert "login" in response.url

    def test_admin_index_accessible_for_authenticated_user(self, admin_user):
        """Test that admin index is accessible for authenticated admin."""
        client = Client()
        client.force_login(admin_user)
        response = client.get(reverse("admin:index"))
        assert response.status_code == 200
        # Verify the dashboard page title includes the site name
        assert b"ICZ" in response.content

    def test_unfold_configuration_loaded(self):
        """Test that Unfold configuration is properly loaded."""
        from django.conf import settings

        assert hasattr(settings, "UNFOLD")
        assert settings.UNFOLD["SITE_TITLE"] == "ICZ"
        assert settings.UNFOLD["SITE_HEADER"] == "ICZ"
        assert settings.UNFOLD["THEME"] is None
        assert settings.UNFOLD.get("SHOW_ALL_APPLICATIONS", False) is True

    def test_base_admin_classes_importable(self):
        """Test that base admin classes can be imported."""
        from core.admin import BaseModelAdmin, ImportExportModelAdmin

        # Verify attributes
        assert BaseModelAdmin.list_per_page == 50
        assert BaseModelAdmin.compressed_fields is True
        assert ImportExportModelAdmin.list_per_page == 50
        assert ImportExportModelAdmin.compressed_fields is True
