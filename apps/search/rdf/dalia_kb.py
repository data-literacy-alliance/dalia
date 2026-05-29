from typing import Union
from uuid import UUID

from rdflib import URIRef

_KB_BASE_URI = "https://id.dalia.education/"
_COMMUNITIES_BASE_URI = _KB_BASE_URI + "community/"
_LEARNING_RESOURCE_BASE_URI = _KB_BASE_URI + "learning-resource/"


def lr_uri(resource_id: Union[UUID, str]) -> str:
    return f"{_LEARNING_RESOURCE_BASE_URI}{resource_id}"


def lr_uri_ref(resource_id: Union[UUID, str]) -> URIRef:
    return URIRef(lr_uri(resource_id))


def community_uri(community_id: Union[UUID, str]) -> str:
    return f"{_COMMUNITIES_BASE_URI}{community_id}"


def community_uri_ref(community_id: Union[UUID, str]) -> URIRef:
    return URIRef(community_uri(community_id))
