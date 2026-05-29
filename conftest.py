"""
Root pytest configuration and fixtures.
"""

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Return a superuser for testing admin functionality."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_superuser(
        username="admin", email="admin@example.com", password="admin123"
    )


@pytest.fixture
def authenticated_client(admin_user):
    """Return an authenticated API client."""
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client
