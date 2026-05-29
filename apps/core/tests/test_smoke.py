"""
Smoke tests for Work Track Pro.

These tests verify basic system integrity and configuration.
"""

import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_django_system_checks_pass():
    """
    Verify that Django system checks pass without errors.

    This smoke test ensures:
    - All apps are properly configured
    - Models are valid
    - Settings are correct
    - No critical configuration issues exist
    """
    call_command("check")
