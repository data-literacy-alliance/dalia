"""
Terms from XQuery, XPath, and XSLT Functions and Operators
"""

from rdflib import URIRef

NS = "http://www.w3.org/2005/xpath-functions#"

# Functions
year_from_date = URIRef(NS + "year-from-date")
month_from_date = URIRef(NS + "month-from-date")
day_from_date = URIRef(NS + "day-from-date")
