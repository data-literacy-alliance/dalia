"""
Wikidata properties
"""

from rdflib import URIRef

NS = "http://www.wikidata.org/prop/direct/"

Mastodon_address = URIRef(NS + "P4033")  # https://www.wikidata.org/wiki/Property:P4033
Bluesky_handle = URIRef(NS + "P12361")  # https://www.wikidata.org/wiki/Property:P12361
Zenodo_communities_ID = URIRef(NS + "P9934")  # https://www.wikidata.org/wiki/Property:P9934
YouTube_channel_ID = URIRef(NS + "P2397")  # https://www.wikidata.org/wiki/Property:P2397
LinkedIn_company_or_organization_ID = URIRef(
    NS + "P4264"
)  # https://www.wikidata.org/wiki/Property:P4264
