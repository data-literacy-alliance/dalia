"""
Terms from Hochschulcampus Ressourcentypen
(https://skohub.io/dini-ag-kim/hcrt/heads/master/w3id.org/kim/hcrt/scheme.html)
"""

from rdflib import URIRef

NS = "https://w3id.org/kim/hcrt/"

# Concept schemes
scheme = URIRef(NS + "scheme")

# Concepts
assessment = URIRef(NS + "assessment")
audio = URIRef(NS + "audio")
case_study = URIRef(NS + "case_study")
course = URIRef(NS + "course")
diagram = URIRef(NS + "diagram")
drill_and_practice = URIRef(NS + "drill_and_practice")
image = URIRef(NS + "image")
lesson_plan = URIRef(NS + "lesson_plan")
index = URIRef(NS + "index")
other = URIRef(NS + "other")
questionnaire = URIRef(NS + "questionnaire")
slide = URIRef(NS + "slide")
text = URIRef(NS + "text")
textbook = URIRef(NS + "textbook")
video = URIRef(NS + "video")
web_page = URIRef(NS + "web_page")
worksheet = URIRef(NS + "worksheet")
