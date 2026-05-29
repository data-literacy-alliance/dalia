from enum import Enum

from django.conf import settings
from rdflib import Literal, Variable
from rdflib.plugins.stores.sparqlstore import SPARQLStore
from rdflib.query import Result

from search.query_builder.query_builder import FILTER, FunctionExpressions, Operators


class Dataset(Enum):
    """
    Dataset names in DALIA's Fuseki triplestore.
    """
    DALIA = "dalia"
    ONTOLOGIES = "ontologies"


def query_dalia_dataset(query: str) -> Result:
    return query_dataset(Dataset.DALIA, query)


def query_ontologies_dataset(query: str) -> Result:
    return query_dataset(Dataset.ONTOLOGIES, query)


def query_dataset(dataset: Dataset, query: str) -> Result:
    sparql_store = _get_sparql_store(dataset) # Get SPARQLStore instance
    #print(f"DEBUG: Executing query against dataset: {dataset.value}, endpoint: {sparql_store.query_endpoint}") # DEBUGGING LOG    
    return _get_sparql_store(dataset).query(query)


# TODO: find out whether we can use one and the same SPARQLStore object for all (parallel) queries
def _get_sparql_store(dataset: Dataset) -> SPARQLStore:
    query_endpoint_url = f"{_get_triplestore_endpoint_from_settings()}{dataset.value}" # Corrected URL
    #print(f"DEBUG: SPARQL Endpoint URL being used: {query_endpoint_url}") # Add this logging
    #print(f"DEBUG: dataset: {dataset.value}") # Add this logging
    #print(f"DEBUG: Function: {_get_triplestore_endpoint_from_settings()}") # Add this logging
    return SPARQLStore(query_endpoint=query_endpoint_url)


def _get_triplestore_endpoint_from_settings() -> str:
    endpoint = getattr(settings, "DALIA_TRIPLESTORE_BASE_URL", "http://localhost:3030/")
    if not endpoint.endswith("/"):
        endpoint += "/"
    return endpoint


def filter_by_lang(var: Variable, lang: str = "en") -> tuple[FILTER]:
    return FILTER(
        Operators.EQ(
            FunctionExpressions.LANG(var),
            Literal(lang)
        )
    )