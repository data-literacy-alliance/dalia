from functools import lru_cache

from rdflib import RDF, URIRef, Variable

from search.api_models.api_models import License
from search.query.utils import query_ontologies_dataset
from search.query_builder.query_builder import FunctionExpressions, OPTIONAL, QueryBuilder, VALUES
from search.rdf.namespace import MoDalia, spdx

_VARIABLES = {
    "licenseId": Variable("licenseId"),
    "name": Variable("name"),
    "url": Variable("url"),
}


def prepare_query_for_license_info(license_uri: URIRef) -> str:
    var_license = Variable("license")
    var_crossref = Variable("crossref")
    var_order = Variable("order")

    return QueryBuilder().SELECT(
        *_VARIABLES.values()
    ).WHERE(
        VALUES(
            [var_license],
            [[license_uri]]
        ),
        (var_license, RDF.type, spdx.ListedLicense),
        OPTIONAL((var_license, spdx.licenseId, _VARIABLES["licenseId"])),
        OPTIONAL((var_license, spdx.name, _VARIABLES["name"])),
        OPTIONAL(
            (var_license, spdx.crossRef_P, var_crossref),
            (var_crossref, RDF.type, spdx.CrossRef_T),
            (var_crossref, spdx.order, var_order),
            (var_crossref, spdx.url, _VARIABLES["url"])
        ),
    ).ORDER_BY(
        FunctionExpressions.ASC(var_order)
    ).LIMIT(1).build()


def _license_from_results(results) -> License:
    if not results:
        return License(
            id="",
            name="",
            link="",
        )

    first_result = next(iter(results))
    return License(
        id=str(first_result.licenseId),
        name=str(first_result.name),
        link=str(first_result.url),
    )


def _proprietary_license():
    return License(
        id="Proprietary",
        name="Proprietary",
        link="",
    )


@lru_cache
def get_license_info(license_uri: URIRef) -> License:
    if license_uri == MoDalia.ProprietaryLicense:
        return _proprietary_license()

    query = prepare_query_for_license_info(license_uri)
    results = query_ontologies_dataset(query)
    return _license_from_results(results)
