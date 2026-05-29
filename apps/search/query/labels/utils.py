from typing import Dict

from rdflib import URIRef

from search.api_models.api_models import LabelValueItem


def remap_to_label_value_item(uri_ref_to_label: Dict[URIRef, str]) -> Dict[URIRef, LabelValueItem]:
    """
    Remap a URIRef to label association to a URIRef to LabelValueItem association.

    :param uri_ref_to_label: URIRef to label association
    :return: URIRef to LabelValueItem association
    """
    return {k: LabelValueItem(label=v, value=str(k)) for k, v in uri_ref_to_label.items()}
