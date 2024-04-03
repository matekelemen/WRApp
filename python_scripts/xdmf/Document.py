""" @author Máté Kelemen"""

__all__ = [
    "Document"
]

# --- WRApp Imports ---
from KratosMultiphysics.WRApplication.xdmf.Domain import Domain

# --- STD Imports ---
from xml.etree.ElementTree import Element



class Document(Element):

    def __init__(self) -> None:
        super().__init__("Xdmf", {"Version" : "3.0"})


    def append(self, domain: Domain) -> None:
        if not isinstance(domain, Domain):
            raise TypeError(f"expecting a Domain, but got {type(domain)}")
        return super().append(domain)
