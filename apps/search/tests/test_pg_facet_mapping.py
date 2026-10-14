"""Tests for search.query.items.search.producers.pg_facet_mapping."""

import pytest

from search.query.items.facets.facet_objects import (
    DISCIPLINE_FACET,
    FILE_FORMAT_FACET,
    LANGUAGE_FACET,
    LICENSE_FACET,
)
from search.query.items.search.producers.pg_facet_mapping import (
    build_reverse_facet_map,
    resolve_facet_value,
)


# ---------------------------------------------------------------------------
# Helpers: simple mock instances (no DB needed for pure-resolver tests)
# ---------------------------------------------------------------------------


class _Obj:
    """Minimal stand-in for a vocab row.  Set any attrs you need."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# ---------------------------------------------------------------------------
# resolve_facet_value — Discipline (URI-based resolver)
# ---------------------------------------------------------------------------


def test_resolve_discipline_known_uri():
    """A Discipline with a recognised URI returns the canonical value string."""
    obj = _Obj(uri="https://w3id.org/kim/hochschulfaechersystematik/n4")
    result = resolve_facet_value(DISCIPLINE_FACET, obj)
    assert result == "https://w3id.org/kim/hochschulfaechersystematik/n4"


def test_resolve_discipline_unknown_uri_returns_none():
    """An unrecognised URI returns None."""
    obj = _Obj(uri="https://example.com/unknown")
    result = resolve_facet_value(DISCIPLINE_FACET, obj)
    assert result is None


def test_resolve_discipline_blank_uri_returns_none():
    """A blank URI returns None without raising."""
    obj = _Obj(uri="")
    result = resolve_facet_value(DISCIPLINE_FACET, obj)
    assert result is None


def test_resolve_discipline_none_uri_returns_none():
    """A None URI returns None without raising."""
    obj = _Obj(uri=None)
    result = resolve_facet_value(DISCIPLINE_FACET, obj)
    assert result is None


def test_resolve_facet_value_never_raises():
    """resolve_facet_value must not propagate exceptions from bad instances."""

    # Instance with no 'uri' attribute at all.
    class Bad:
        @property
        def uri(self):
            raise RuntimeError("boom")

    result = resolve_facet_value(DISCIPLINE_FACET, Bad())
    assert result is None


# ---------------------------------------------------------------------------
# File-format resolver (label-based, case-insensitive; leading dot stripped)
# ---------------------------------------------------------------------------


def test_resolve_file_format_exact_label():
    """A FileFormat with label 'PDF' maps to the 'PDF' canonical value."""
    obj = _Obj(uri="", label="PDF", slug="pdf")
    result = resolve_facet_value(FILE_FORMAT_FACET, obj)
    assert result == "PDF"


def test_resolve_file_format_leading_dot_via_slug():
    """A FileFormat whose label is '.pdf' misses the exact match; slug 'pdf' maps to 'PDF'."""
    obj = _Obj(uri="", label=".pdf", slug="pdf")
    result = resolve_facet_value(FILE_FORMAT_FACET, obj)
    assert result == "PDF"


def test_resolve_file_format_lowercase_label():
    """Case-insensitive: 'html' label maps to 'HTML'."""
    obj = _Obj(uri="", label="html", slug="html")
    result = resolve_facet_value(FILE_FORMAT_FACET, obj)
    assert result == "HTML"


def test_resolve_file_format_blank_label_returns_none():
    """A blank label returns None."""
    obj = _Obj(uri="", label="", slug="")
    result = resolve_facet_value(FILE_FORMAT_FACET, obj)
    assert result is None


# ---------------------------------------------------------------------------
# Language resolver (ISO 639-1 code → lexvo URI)
# ---------------------------------------------------------------------------


def test_resolve_language_by_code_en():
    """Language with code 'en' resolves to the lexvo English URI."""
    obj = _Obj(uri="", code="en")
    result = resolve_facet_value(LANGUAGE_FACET, obj)
    assert result == "http://lexvo.org/id/iso639-3/eng"


def test_resolve_language_by_code_de():
    obj = _Obj(uri="", code="de")
    assert resolve_facet_value(LANGUAGE_FACET, obj) == "http://lexvo.org/id/iso639-3/deu"


def test_resolve_language_by_code_fr():
    obj = _Obj(uri="", code="fr")
    assert resolve_facet_value(LANGUAGE_FACET, obj) == "http://lexvo.org/id/iso639-3/fra"


def test_resolve_language_by_code_es():
    obj = _Obj(uri="", code="es")
    assert resolve_facet_value(LANGUAGE_FACET, obj) == "http://lexvo.org/id/iso639-3/spa"


def test_resolve_language_by_uri_directly():
    """A Language with the lexvo URI directly set on .uri resolves correctly."""
    obj = _Obj(uri="http://lexvo.org/id/iso639-3/eng", code="")
    result = resolve_facet_value(LANGUAGE_FACET, obj)
    assert result == "http://lexvo.org/id/iso639-3/eng"


def test_resolve_language_unknown_code_returns_none():
    obj = _Obj(uri="", code="zz")
    assert resolve_facet_value(LANGUAGE_FACET, obj) is None


# ---------------------------------------------------------------------------
# License resolver (uri first, then spdx_id fallback)
# ---------------------------------------------------------------------------


def test_resolve_license_by_uri():
    """A License with a recognised SPDX URI maps to the canonical value."""
    obj = _Obj(uri="http://spdx.org/licenses/CC-BY-4.0", spdx_id="")
    result = resolve_facet_value(LICENSE_FACET, obj)
    assert result == "http://spdx.org/licenses/CC-BY-4.0"


def test_resolve_license_by_spdx_id():
    """A License with blank URI but valid spdx_id maps via derived URL."""
    obj = _Obj(uri="", spdx_id="CC-BY-4.0")
    result = resolve_facet_value(LICENSE_FACET, obj)
    assert result == "http://spdx.org/licenses/CC-BY-4.0"


def test_resolve_license_blank_both_returns_none():
    obj = _Obj(uri="", spdx_id="")
    assert resolve_facet_value(LICENSE_FACET, obj) is None


def test_resolve_license_unknown_spdx_returns_none():
    obj = _Obj(uri="", spdx_id="UNKNOWN-9.9")
    assert resolve_facet_value(LICENSE_FACET, obj) is None


# ---------------------------------------------------------------------------
# build_reverse_facet_map — DB required, uses vocab tables
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_build_reverse_facet_map_returns_dict():
    """build_reverse_facet_map returns a dict (may be empty if no vocab rows exist)."""
    result = build_reverse_facet_map(DISCIPLINE_FACET)
    assert isinstance(result, dict)


@pytest.mark.django_db
def test_build_reverse_facet_map_skips_blank_uri(django_db_setup):
    """Rows with blank URI are excluded from the reverse map."""
    from curation.models.vocabularies import Discipline

    disc = Discipline.objects.create(
        label="Blank URI Discipline Test",
        uri="",
        is_active=True,
    )
    result = build_reverse_facet_map(DISCIPLINE_FACET)
    # The blank-URI row's PK must not appear in any value set.
    all_pks = {pk for pks in result.values() for pk in pks}
    assert disc.pk not in all_pks
    disc.delete()


@pytest.mark.django_db
def test_build_reverse_facet_map_maps_known_uri():
    """A Discipline row with a known URI appears in the reverse map."""
    from curation.models.vocabularies import Discipline

    known_uri = "https://w3id.org/kim/hochschulfaechersystematik/n4"
    disc = Discipline.objects.create(
        label="Mathematics Test Disc",
        uri=known_uri,
        is_active=True,
    )
    result = build_reverse_facet_map(DISCIPLINE_FACET)
    assert known_uri in result
    assert disc.pk in result[known_uri]
    disc.delete()
