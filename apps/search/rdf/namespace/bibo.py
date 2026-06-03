"""
Terms from the Bibliographic Ontology (https://dcmi.github.io/bibo/)
"""

from rdflib import URIRef

NS = "http://purl.org/ontology/bibo/"

# Types
Article = URIRef(NS + "Article")
Book = URIRef(NS + "Book")
Report = URIRef(NS + "Report")
Webpage = URIRef(NS + "Webpage")
