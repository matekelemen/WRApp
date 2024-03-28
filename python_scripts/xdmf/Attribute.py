""" @author Máté Kelemen"""

__all__ = [
    "Attribute",
    "NodeAttribute",
    "CellAttribute",
    "GridAttribute"
]

# --- WRApp Imports ---
from KratosMultiphysics.WRApplication.xdmf.DataItem import DataItem

# --- STD Imports ---
from xml.etree.ElementTree import Element



class Attribute(Element):

    def __init__(self,
                 name: str,
                 data_item: DataItem) -> None:
        super().__init__("Attribute", {})
        self.attrib["Name"] = name
        shape = data_item.attrib["Dimensions"].split(" ")
        if len(shape) < 3:
            self.attrib["AttributeType"] = "Scalar"
        elif len(shape) == 3:
            self.attrib["AttributeType"] = "Vector"
        else:
            self.attrib["AttributeType"] = "Matrix"
        self.append(data_item)



class NodeAttribute(Attribute):

    def __init__(self, name: str, data_item: DataItem) -> None:
        super().__init__(name, data_item)
        self.attrib["Center"] = "Node"



class CellAttribute(Attribute):

    def __init__(self, name: str, data_item: DataItem) -> None:
        super().__init__(name, data_item)
        self.attrib["Center"] = "Cell"



class GridAttribute(Attribute):

    def __init__(self, name: str, data_item: DataItem) -> None:
        super().__init__(name, data_item)
        self.attrib["Center"] = "Grid"
