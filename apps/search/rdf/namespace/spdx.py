"""
Terms from spdx.org
"""

from rdflib import URIRef

NS = "http://spdx.org/rdf/terms#"

# Properties
crossRef_P = URIRef(NS + "crossRef")
isDeprecatedLicenseId = URIRef(NS + "isDeprecatedLicenseId")
licenseId = URIRef(NS + "licenseId")
licenseText = URIRef(NS + "licenseText")
name = URIRef(NS + "name")
order = URIRef(NS + "order")
url = URIRef(NS + "url")

# Types
CrossRef_T = URIRef(NS + "CrossRef")
ListedLicense = URIRef(NS + "ListedLicense")
