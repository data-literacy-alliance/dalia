"""
Tests for core health check endpoint.
"""

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_health_check_returns_200(api_client):
    """Test that the health check endpoint returns 200 OK."""
    url = reverse("core:health-check")
    response = api_client.get(url)

    assert response.status_code == 200
    assert response.data["status"] == "healthy"
    assert "version" in response.data
    assert "cache" in response.data
