"""
Terms from FaBiO, the FRBR-aligned Bibliographic Ontology
"""
from rdflib import URIRef

NS = "http://purl.org/spar/fabio/"

# Properties
hasDiscipline = URIRef(NS + "hasDiscipline")  # https://sparontologies.github.io/fabio/current/fabio.html#d4e205
hasSubtitle = URIRef(NS + "hasSubtitle")  # https://sparontologies.github.io/fabio/current/fabio.html#d4e1689
