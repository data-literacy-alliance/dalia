from typing import Dict, List, Optional

from rdflib import BNode, Graph, Literal, RDF, Variable, XSD
from rdflib.collection import Collection
from rdflib.term import Node, URIRef

from search.query.items.facets.facet_objects import COMMUNITY_FACET, FacetObject
from search.query_builder.query_builder import (
    BIND,
    FILTER,
    FILTER_EXISTS,
    GROUP,
    OPTIONAL,
    Operators,
    UNION,
    VALUES,
)
from search.rdf.namespace import (
    bibframe_lite_relation,
    Dalia_text,
    Jena_text,
    MoDalia,
    rec,
    SCHEMA,
    educor,
)


class _MultiTypeDateExpr:
    """
    Raw SPARQL expression for date range filtering that handles three date formats:
      xsd:date       e.g. "2024-06-03"
      xsd:gYearMonth e.g. "2024-02"
      xsd:gYear      e.g. "2023"

    Passed to FILTER() which only requires the object to have an .n3() method.
    """

    XSD = "http://www.w3.org/2001/XMLSchema#"

    def __init__(self, op: str, full_date: str, year_month: str, year: str, var):
        self._op = op  # ">=" or "<="
        self._full = full_date  # "2022-12-06"
        self._ym = year_month  # "2022-12"
        self._yr = year  # "2022"
        self._var = var.n3()  # "?datePublished"

    def n3(self) -> str:
        xsd = self.XSD
        op = self._op
        v = self._var
        return (
            f"("
            f'  (DATATYPE({v}) = <{xsd}date> && {v} {op} "{self._full}"^^<{xsd}date>)'
            f'  || (DATATYPE({v}) = <{xsd}gYearMonth> && str({v}) {op} "{self._ym}")'
            f'  || (DATATYPE({v}) = <{xsd}gYear> && str({v}) {op} "{self._yr}")'
            f")"
        )


def _is_browse_all_query(query: str) -> bool:
    """Check if the query is a browse all request (wildcard or empty)."""
    if not query:
        return True
    stripped = query.strip()
    return stripped == "" or stripped == "*" or stripped == "**"


def _prepare_lucene_query(query: str) -> str:
    """
    Prepare query string for Lucene text search using AND logic.
    Converts multi-word queries to require all terms (+prefix).
    """
    if not query:
        return query
    stripped = query.strip()
    if any(op in stripped for op in ["+", "-", "AND", "OR", '"']):
        return stripped
    terms = [term.strip() for term in stripped.split() if term.strip()]
    if len(terms) <= 1:
        return stripped
    return " ".join(f"+{term}" for term in terms)


def prepare_where_for_text_search_for_learning_resources(
    query: str,
    active_facets: Dict[FacetObject, List[Node]],
    var_lr: Variable,
    var_score: Variable,
    var_created: Variable,
    date_published_after: Optional[str] = None,
    date_published_before: Optional[str] = None,
):
    """
    Prepare SPARQL WHERE clause for learning resource search.

    Two modes:
    1. Browse All (query is "*" or empty): simple SELECT without text search
    2. Text Search: full-text search using Jena text index

    Both modes support:
    - Facet filtering (OR within category via VALUES, AND between categories)
    - Date range filtering (after/before/between)
    """

    if _is_browse_all_query(query):
        # Browse All Mode: simple query without text search
        where = [
            (var_lr, RDF.type, educor.EducationalResource),
            OPTIONAL((var_lr, SCHEMA.datePublished, var_created)),
            FILTER_EXISTS((var_lr, RDF.type, MoDalia.Community), state=False),
        ]
    else:
        # Text Search Mode: use Jena full-text search index
        var_s = Variable("s")
        var_type = Variable("type")

        lucene_query = _prepare_lucene_query(query)

        left_list = Collection(Graph(), BNode(), [var_s, var_score])
        right_list = Collection(
            Graph(), BNode(), [Dalia_text.learningResourceTexts, Literal(lucene_query)]
        )

        # GROUP+UNION (not OPTIONALs) so ?lr is always bound from the text-search
        # paths before facet filter triples are appended.  With OPTIONALs, ?lr
        # could be unbound when the hit was neither an ER nor a Person/Org; the
        # subsequent facet triple would then bind ?lr to every resource in the
        # triplestore with that predicate, inflating counts (issue #106).
        where = [
            (left_list, Jena_text.query, right_list),
            GROUP(
                (var_s, RDF.type, var_type),
                FILTER(
                    Operators.OR(
                        Operators.EQ(var_type, SCHEMA.Person),
                        Operators.EQ(var_type, SCHEMA.Organization),
                    )
                ),
                (var_lr, URIRef("https://dalia.education/authorUnordered"), var_s),
                OPTIONAL((var_lr, SCHEMA.datePublished, var_created)),
            ),
            UNION(
                (var_s, RDF.type, educor.EducationalResource),
                OPTIONAL((var_s, SCHEMA.datePublished, var_created)),
                BIND(var_s, var_lr),
            ),
            FILTER_EXISTS((var_lr, RDF.type, MoDalia.Community), state=False),
        ]

    # Facet filters - OR within category (VALUES), AND between categories (separate clauses)
    for facet, active_facet_items in active_facets.items():
        if active_facet_items:
            var_name = facet.label.replace(" ", "_").replace("-", "_")
            var_facet_value = Variable(f"facetValue_{var_name}")

            where.append(VALUES([var_facet_value], [(item,) for item in active_facet_items]))
            if facet is COMMUNITY_FACET:
                # hasCommunity predicate does not exist in Fuseki; community membership
                # is expressed via rec:recommender (or bflr:supportinghost for future data).
                where.append(GROUP((var_lr, rec.recommender, var_facet_value)))
                where.append(
                    UNION((var_lr, bibframe_lite_relation.supportinghost, var_facet_value))
                )
            else:
                where.append((var_lr, facet.predicate, var_facet_value))

    # Date range filtering — handles xsd:date, xsd:gYearMonth, xsd:gYear
    if date_published_after or date_published_before:
        var_date = Variable("datePublished")
        where.append((var_lr, SCHEMA.datePublished, var_date))

        if date_published_after:
            year = date_published_after[:4]
            year_month = date_published_after[:7]
            where.append(
                FILTER(_MultiTypeDateExpr(">=", date_published_after, year_month, year, var_date))
            )

        if date_published_before:
            year = date_published_before[:4]
            year_month = date_published_before[:7]
            where.append(
                FILTER(_MultiTypeDateExpr("<=", date_published_before, year_month, year, var_date))
            )

    return tuple(where)
