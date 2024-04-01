""" @author Máté Kelemen"""

__all__ = [
    "Geometry"
]

# --- WRApp Imports ---
from KratosMultiphysics.WRApplication.xdmf.DataItem import DataItem

# --- STD Imports ---
from xml.etree.ElementTree import Element
from enum import Enum



class Geometry(Element):

    class Type(Enum):
        XYZ             = 0
        XY              = 1
        X_Y_Z           = 2
        VXVYVZ          = 3
        ORIGIN_DXDYDZ   = 4
        ORIGIN_DXDY     = 5


    def __init__(self, geometry_type: "Geometry.Type") -> None:
        super().__init__("Geometry")
        if not isinstance(geometry_type, Geometry.Type):
            raise TypeError(f"expecting Geometry.Type, but got {type(geometry_type)}")
        self.attrib["GeometryType"] = geometry_type.name


    def append(self, child: DataItem) -> None:
        if not isinstance(child, DataItem):
            raise TypeError(f"expecting a DataItem, but got {type(child)}")
        return super().append(child)
