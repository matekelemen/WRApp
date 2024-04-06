""" @author Máté Kelemen"""

__all__ = [
    "Attribute"
]

# --- WRApp Imports ---
from KratosMultiphysics.WRApplication.xdmf.DataItem import DataItem

# --- STD Imports ---
from xml.etree.ElementTree import Element
from enum import Enum



class Attribute(Element):

    class Center(Enum):
        Node = 0
        Cell = 1
        Grid = 2


    def __init__(self,
                 name: str,
                 attribute_center: "Attribute.Center") -> None:
        super().__init__("Attribute", {})
        self.attrib["Name"] = name
        self.attrib["Center"] = attribute_center.name


    def append(self, data_item: DataItem) -> None:
        if len(self) != 0:
            raise RuntimeError(f"attribute {self.attrib['Name']} is already set")
        if not isinstance(data_item, DataItem):
            raise TypeError(f"expecting a DataItem, but got {type(data_item)}")

        shape = data_item.GetShape()
        if len(shape) == 1 or (len(shape) == 2 and shape[1] == 1):
            self.attrib["AttributeType"] = "Scalar"
        elif len(shape) == 2:
            self.attrib["AttributeType"] = "Vector"
        elif len(shape) == 3:
            self.attrib["AttributeType"] = "Matrix"
        else:
            raise RuntimeError(f"unsupported shape: {shape}")

        return super().append(data_item)
