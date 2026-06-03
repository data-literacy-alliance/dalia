"""
Terms from the MoDalia ontology (https://git.rwth-aachen.de/dalia/dalia-ontology/-/blob/main/MoDalia.ttl)
"""

from rdflib import URIRef

NS = "https://purl.org/ontology/modalia#"

# Properties
hasLearningType = URIRef(NS + "hasLearningType")
hasMediaType = URIRef(NS + "hasMediaType")
hasTargetGroup = URIRef(NS + "hasTargetGroup")
hasOrder = URIRef(NS + "hasOrder")
isRelatedTo = URIRef(NS + "isRelatedTo")
requiresProficiencyLevel = URIRef(NS + "requiresProficiencyLevel")

# Types
BachelorStudent = URIRef(NS + "BachelorStudent")
BestPractices = URIRef(NS + "BestPractices")
Code = URIRef(NS + "Code")
CodeNotebook = URIRef(NS + "CodeNotebook")
Community = URIRef(NS + "Community")
Cookbook = URIRef(NS + "Cookbook")
ContentProvider = URIRef(NS + "ContentProvider")
DataSteward = URIRef(NS + "DataSteward")
LearningResourceType = URIRef(NS + "LearningResourceType")
Lecture = URIRef(NS + "Lecture")
MastersStudent = URIRef(NS + "MastersStudent")
MediaType = URIRef(NS + "MediaType")
Multipart = URIRef(NS + "Multipart")
PhDStudent = URIRef(NS + "PhDStudent")
Poster = URIRef(NS + "Poster")
Proficiency = URIRef(NS + "Proficiency")
Researcher = URIRef(NS + "Researcher")
StudentSchool = URIRef(NS + "StudentSchool")
TargetGroup = URIRef(NS + "TargetGroup")
TeacherHighEducation = URIRef(NS + "TeacherHighEducation")
TeacherSchool = URIRef(NS + "TeacherSchool")
Tutorial = URIRef(NS + "Tutorial")
Workshop = URIRef(NS + "Workshop")

# Individuals
Beginner = URIRef(NS + "Beginner")
Competent = URIRef(NS + "Competent")
Expert = URIRef(NS + "Expert")
Novice = URIRef(NS + "Novice")
Proficient = URIRef(NS + "Proficient")
ProprietaryLicense = URIRef(NS + "ProprietaryLicense")
