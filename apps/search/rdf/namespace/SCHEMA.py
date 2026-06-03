"""
Terms from schema.org
"""

from rdflib import URIRef

NS = "https://schema.org/"

# Properties
author = URIRef(NS + "author")
datePublished = URIRef(NS + "datePublished")
familyName = URIRef(NS + "familyName")
fileSize = URIRef(NS + "fileSize")
givenName = URIRef(NS + "givenName")
keywords = URIRef(NS + "keywords")
name = URIRef(NS + "name")
url = URIRef(NS + "url")

# Types
AudioObject = URIRef(NS + "AudioObject")
ImageObject = URIRef(NS + "ImageObject")
Organization = URIRef(NS + "Organization")
Person = URIRef(NS + "Person")
PodcastSeries = URIRef(NS + "PodcastSeries")
PresentationDigitalDocument = URIRef(NS + "PresentationDigitalDocument")
SoftwareSourceCode = URIRef(NS + "SoftwareSourceCode")
Text = URIRef(NS + "Text")
VideoObject = URIRef(NS + "VideoObject")
