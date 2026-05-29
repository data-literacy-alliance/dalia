from collections import defaultdict
from typing import Dict, List, Union

from rdflib import RDF, URIRef, Variable

from search.api_models.api_models import OrganizationAuthor, PersonAuthor
from search.query.utils import query_dalia_dataset
from search.query_builder.query_builder import GROUP, OPTIONAL, QueryBuilder, UNION, VALUES
from search.rdf.namespace import Jena_ARQ_list, SCHEMA, educor, metadata4ing

_VARIABLES = {
    "lr": Variable("lr"),
    "type": Variable("type"),
    "name": Variable("name"),
    "family": Variable("family"),
    "given": Variable("given"),
    "orcid": Variable("orcid"),
}


def prepare_query_for_authors_metadata_for_resources(resource_uri_refs: List[URIRef]) -> str:
    var_lr = _VARIABLES["lr"]
    var_list = Variable("list")
    var_member = Variable("member")

    resource_uri_ref_blocks = [[uri_ref] for uri_ref in resource_uri_refs]

    return QueryBuilder().SELECT(
        *_VARIABLES.values()
    ).WHERE(
        VALUES(
            [var_lr],
            resource_uri_ref_blocks
        ),
        (var_lr, RDF.type, educor.EducationalResource),
        (var_lr, SCHEMA.author, var_list),
        (var_list, Jena_ARQ_list.member, var_member),
        (var_member, RDF.type, _VARIABLES["type"]),
        GROUP(
            (var_member, RDF.type, SCHEMA.Organization),
            (var_member, SCHEMA.name, _VARIABLES["name"])
        ),
        UNION(
            (var_member, RDF.type, SCHEMA.Person),
            (var_member, SCHEMA.familyName, _VARIABLES["family"]),
            OPTIONAL(
                (var_member, SCHEMA.givenName, _VARIABLES["given"])
            ),
            OPTIONAL(
                (var_member, metadata4ing.orcidId, _VARIABLES["orcid"])
            )
        )
    ).build()


def authors_from_results(
        results
) -> Dict[URIRef, List[Union[PersonAuthor, OrganizationAuthor]]]:
    lr_authors = defaultdict(list)

    for result in results:
        type = result.type
        if type == SCHEMA.Organization:
            name = str(result.name) if result.name else None
            author = OrganizationAuthor(name=name)
        elif type == SCHEMA.Person:
            given = str(result.given) if result.given else None
            family = str(result.family) if result.family else None
            orcid = str(result.orcid) if result.orcid else None
            author = PersonAuthor(firstname=given, lastname=family, orcid=orcid)
        else:
            continue

        lr_authors[result.lr].append(author)

    return lr_authors


def get_authors_metadata_for_resources(
        resource_uri_refs: List[URIRef]
) -> Dict[URIRef, List[Union[PersonAuthor, OrganizationAuthor]]]:
    """
    Retrieve the authors metadata for each of the given learning resource URIRefs.

    :param resource_uri_refs: List of learning resource URIRefs
    :return: Associations between the learning resource URIRefs and their respective list of authors.
    """
    query = prepare_query_for_authors_metadata_for_resources(resource_uri_refs)

    results = query_dalia_dataset(query)
    return authors_from_results(results)
