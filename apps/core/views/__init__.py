"""
Core views package.
Re-exports all views for backward compatibility.
"""

from core.views.base import admin_logout, health_check  # noqa: F401

__all__ = ["admin_logout", "health_check"]
