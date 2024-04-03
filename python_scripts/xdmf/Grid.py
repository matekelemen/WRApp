""" @author Máté Kelemen"""

__all__ = [
    "Grid",
    "GridLeaf",
    "GridCollection",
    "GridTree",
    "GridSubset"
]

# --- WRApp Imports ---
from KratosMultiphysics.WRApplication.xdmf.DataItem import DataItem
from KratosMultiphysics.WRApplication.xdmf.Time import Time
from KratosMultiphysics.WRApplication.xdmf.Topology import Topology
from KratosMultiphysics.WRApplication.xdmf.Geometry import Geometry
from KratosMultiphysics.WRApplication.xdmf.Attribute import Attribute

# --- STD Imports ---
from xml.etree.ElementTree import Element
from enum import Enum
from typing import Optional, Union



class Grid(Element):

    def __init__(self, name: str) -> None:
        super().__init__("Grid")
        self.attrib["Name"] = name



class GridLeaf(Grid):

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.attrib["GridType"] = "Uniform"


    def append(self, item: Union[Time, Topology, Geometry, Attribute]) -> None:
        if not isinstance(item, (Time, Topology, Geometry, Attribute)):
            raise TypeError(f"expecting a Topology, Geometry or Attribute, but got {type(item)}")
        return super().append(item)



class GridCollection(Grid):


    class Type(Enum):
        Spatial     = 0
        Temporal    = 1


    def __init__(self,
                 name: str,
                 collection_type: "Optional[GridCollection.Type]" = None) -> None:
        super().__init__(name)
        self.attrib["GridType"] = "Collection"
        if collection_type is not None:
            if not isinstance(collection_type, GridCollection.Type):
                raise TypeError(f"expecting a GridCollection.Type, but got {type(collection_type)}")
            self.attrib["CollectionType"] = collection_type.name


    def append(self, grid: Union[Grid, Time]) -> None:
        if not isinstance(grid, (Grid, Time)):
            raise TypeError(f"expecting a Grid, but got {type(grid)}")
        return super().append(grid)



class GridTree(Grid):

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.attrib["GridType"] = "Tree"


    def append(self, grid: Union[Grid, Time]) -> None:
        if not isinstance(grid, (Grid, Time)):
            raise TypeError(f"expecting a Grid, but got {type(grid)}")
        return super().append(grid)



class GridSubset(Grid):

    def __init__(self,
                 name: str,
                 reference_grid_path: str,
                 index_set: Optional[DataItem] = None) -> None:
        super().__init__(name)
        if index_set is None:
            self.attrib["Section"] = "All"
        else:
            self.attrib["Section"] = "DataItem"
            super().append(index_set)

        reference_pointer = Element("Grid", {"Reference" : "XML"})
        reference_pointer.text = reference_grid_path
        super().append(reference_pointer)


    def append(self, item: Union[Time, Topology, Geometry, Attribute]) -> None:
        if not isinstance(item, (Time, Topology, Geometry, Attribute)):
            raise TypeError(f"expecting a Topology, Geometry or Attribute, but got {type(item)}")
        return super().append(item)
