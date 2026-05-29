"""
Testing settings for ICZ.
Uses SQLite for speed and DummyBackend for tasks.
"""

from .base import *  # noqa: F403, F405

# Override database to use SQLite for fast tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Override cache backend for tests (use in-memory instead of Redis)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}

# Use DummyBackend for tasks in tests
TASKS = {
    "default": {
        "BACKEND": "django_tasks.backends.dummy.DummyBackend",
    },
}

# Disable password hashers for faster tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable migrations for faster tests
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()

# Disable axes in tests
AXES_ENABLED = False

# Speed up tests
DEBUG = False
