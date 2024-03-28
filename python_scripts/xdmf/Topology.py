""" @author Máté Kelemen"""

__all__ = [
    "Topology"
]

# --- WRApp Imports ---
from KratosMultiphysics.WRApplication.xdmf.DataItem import DataItem

# --- STD Imports ---
from xml.etree.ElementTree import Element
from enum import Enum
from typing import Optional



class Topology(Element):


    class Type(Enum):
        Mixed           = 0
        Polyvertex      = 1
        Polyline        = 2
        Polygon         = 3
        Triangle        = 4
        Quadrilateral   = 5
        Tetrahedron     = 6
        Pyramid         = 7
        Wedge           = 8
        Hexahedron      = 9
        Edge_3          = 10
        Triangle_6      = 11
        Quadrilateral_8 = 12
        Tetrahedron_10  = 13
        Pyramid_13      = 14
        Wedge_15        = 15
        Hexahedron_20   = 16
        Mesh2DS         = 17
        Mesh2DRect      = 18
        Mesh2DCoRect    = 19
        Mesh3DS         = 20
        Mesh3DRect      = 21
        Mesh3DCoRect    = 22


    def __init__(self,
                 topology_type: "Type",
                 element_count: int,
                 nodes_per_element: Optional[int] = None) -> None:
        super().__init__("Topology")

        if not isinstance(topology_type, Topology.Type):
            raise TypeError(f"expecting Topology.Type, but got {type(topology_type)}")

        if nodes_per_element is None:
            nodes_per_element = self.GetNodesPerElement(topology_type)
            if nodes_per_element is None:
                raise RuntimeError(f"failed to deduce number of nodes per element from topology type {topology_type.name}")

        self.attrib["TopologyType"] = topology_type.name
        self.attrib["NumberOfElements"] = str(element_count)
        self.attrib["NodesPerElement"] = str(nodes_per_element)


    def append(self, child: DataItem) -> None:
        if not isinstance(child, DataItem):
            raise TypeError(f"expecting a DataItem, but got {type(child)}")
        return super().append(child)


    @staticmethod
    def GetNodesPerElement(topology_type: "Topology.Type") -> Optional[int]:
        return {
            Topology.Type.Mixed             : None,
            Topology.Type.Polyvertex        : 1,
            Topology.Type.Polyline          : 2,
            Topology.Type.Polygon           : None,
            Topology.Type.Triangle          : 3,
            Topology.Type.Quadrilateral     : 4,
            Topology.Type.Tetrahedron       : 4,
            Topology.Type.Pyramid           : 5,
            Topology.Type.Wedge             : 6,
            Topology.Type.Hexahedron        : 8,
            Topology.Type.Edge_3            : 3,
            Topology.Type.Triangle_6        : 6,
            Topology.Type.Quadrilateral_8   : 8,
            Topology.Type.Tetrahedron_10    : 10,
            Topology.Type.Pyramid_13        : 13,
            Topology.Type.Wedge_15          : 15,
            Topology.Type.Hexahedron_20     : 20,
            Topology.Type.Mesh2DS           : None,
            Topology.Type.Mesh2DRect        : None,
            Topology.Type.Mesh2DCoRect      : None,
            Topology.Type.Mesh3DS           : None,
            Topology.Type.Mesh3DRect        : None,
            Topology.Type.Mesh3DCoRect      : None
        }.get(topology_type, None)
