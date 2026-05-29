from typing import Dict, List

from django.utils.text import slugify
from rdflib import DCTERMS, RDF, URIRef, Variable

from search.api_models.api_models import License, Resource
from search.query.items.metadata.license import get_license_info
from search.query.utils import query_dalia_dataset
from search.query_builder.query_builder import FILTER, FunctionExpressions, OPTIONAL, QueryBuilder, VALUES
from search.rdf.namespace import MoDalia, SCHEMA, educor, fabio

_VARIABLES = {
    "lr": Variable("lr"),
    "description": Variable("description"),
    "title": Variable("title"),
    "subtitle": Variable("subtitle"),
    "created": Variable("created"),
    "license": Variable("license"),
    "fileSize": Variable("fileSize"),
    "url": Variable("url"),
}


def prepare_query_for_one_to_one_metadata_for_resources(resource_uri_refs: List[URIRef]) -> str:
    var_lr = _VARIABLES["lr"]

    resource_uri_ref_blocks = [[uri_ref] for uri_ref in resource_uri_refs]

    return QueryBuilder().SELECT(
        *_VARIABLES.values()
    ).WHERE(
        VALUES(
            [var_lr],
            resource_uri_ref_blocks
        ),
        (var_lr, RDF.type, educor.EducationalResource),
        OPTIONAL((var_lr, DCTERMS.description, _VARIABLES["description"])),
        OPTIONAL((var_lr, DCTERMS.title, _VARIABLES["title"])),
        OPTIONAL((var_lr, fabio.hasSubtitle, _VARIABLES["subtitle"])),
        OPTIONAL((var_lr, SCHEMA.datePublished, _VARIABLES["created"])),
        OPTIONAL((var_lr, DCTERMS.license, _VARIABLES["license"])),
        OPTIONAL((var_lr, SCHEMA.fileSize, _VARIABLES["fileSize"])),
        OPTIONAL((var_lr, SCHEMA.url, _VARIABLES["url"])),
    ).build()


def process_result_for_one_to_one_metadata_for_resources(result) -> Resource:
    resource = Resource()

    resource.id = str(result.lr).split("/")[-1]
    resource.title = str(result.title) if not result.subtitle else str(result.title) + ": " + str(result.subtitle)
    resource.description = str(result.description) if result.description else ""
    resource.url = str(result.url)
    resource.license = get_license_info(result.license) if result.license else License(id="", name="", link="")
    resource.publication_date = str(result.created) if result.created else None
    resource.file_size = str(result.fileSize) if result.fileSize else None

    # TODO: could this be moved to the dataclass definition using the @property decorator?
    resource.slug = slugify(resource.title)

    return resource


def get_one_to_one_metadata_for_resources(resource_uri_refs: List[URIRef]) -> Dict[URIRef, Resource]:
    """
    Retrieve the 1-to-1 metadata for each of the given learning resource URIRefs.

    :param resource_uri_refs: List of learning resource URIRefs
    :return: Associations between the learning resource URIRefs and their respective metadata.
    """
    if not resource_uri_refs:
        return {}

    query = prepare_query_for_one_to_one_metadata_for_resources(resource_uri_refs)

    results = query_dalia_dataset(query)
    return {result.lr: process_result_for_one_to_one_metadata_for_resources(result) for result in results}
