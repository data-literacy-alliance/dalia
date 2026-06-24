"""Tests for search.query.items.search.sources.get_enabled_search_sources."""

import pytest
from django.test import override_settings

from search.query.items.search.sources import get_enabled_search_sources


def test_default_missing_setting():
    """Missing DALIA_SEARCH_SOURCES falls back to fuseki."""
    with override_settings(DALIA_SEARCH_SOURCES=None):
        result = get_enabled_search_sources()
    assert result == ["fuseki"]


def test_empty_list_falls_back():
    """Empty list falls back to fuseki."""
    with override_settings(DALIA_SEARCH_SOURCES=[]):
        result = get_enabled_search_sources()
    assert result == ["fuseki"]


def test_bogus_source_falls_back():
    """A list of only unrecognised sources falls back to fuseki."""
    with override_settings(DALIA_SEARCH_SOURCES=["bogus"]):
        result = get_enabled_search_sources()
    assert result == ["fuseki"]


def test_non_list_string_falls_back():
    """A bare string (not a list) falls back to fuseki."""
    with override_settings(DALIA_SEARCH_SOURCES="fuseki"):
        result = get_enabled_search_sources()
    assert result == ["fuseki"]


def test_both_sources_unchanged():
    """Both valid sources are returned unchanged."""
    with override_settings(DALIA_SEARCH_SOURCES=["fuseki", "postgres"]):
        result = get_enabled_search_sources()
    assert result == ["fuseki", "postgres"]


def test_deduplication():
    """Duplicate source names are collapsed to a single entry."""
    with override_settings(DALIA_SEARCH_SOURCES=["fuseki", "fuseki", "postgres"]):
        result = get_enabled_search_sources()
    assert result == ["fuseki", "postgres"]


def test_whitespace_stripped():
    """Source names with surrounding whitespace are accepted after stripping."""
    with override_settings(DALIA_SEARCH_SOURCES=[" fuseki ", "postgres"]):
        result = get_enabled_search_sources()
    assert result == ["fuseki", "postgres"]


def test_postgres_only():
    """Single postgres source is accepted without falling back."""
    with override_settings(DALIA_SEARCH_SOURCES=["postgres"]):
        result = get_enabled_search_sources()
    assert result == ["postgres"]
