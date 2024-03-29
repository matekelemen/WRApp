""" @author Máté Kelemen"""

# --- External Imports ---
#try:
#    import h5py
#except ModuleNotFoundError:
#    class h5py:
#        class Group: pass
#        class Dataset: pass
import h5py

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
from KratosMultiphysics.WRApplication.xdmf.DataType import Int, Double
from KratosMultiphysics.WRApplication.xdmf.Data import HDF5Data
from KratosMultiphysics.WRApplication.xdmf.DataItem import DataItem, LeafDataItem, CoordinateDataItem
from KratosMultiphysics.WRApplication.xdmf.Attribute import NodeAttribute, CellAttribute, GridAttribute
from KratosMultiphysics.WRApplication.xdmf.Topology import Topology
from KratosMultiphysics.WRApplication.xdmf.Geometry import Geometry
from KratosMultiphysics.WRApplication.xdmf.Grid import Grid, GridTree, GridCollection, GridLeaf

# --- STD Imports ---
from typing import Optional
import pathlib
import re
from enum import Enum



__CELL_MAP : "dict[tuple[int,int],list[Topology.Type]]" = {
    (2, 1)  : [Topology.Type.Polyvertex],
    (2, 2)  : [Topology.Type.Polyline],
    (2, 3)  : [Topology.Type.Triangle, Topology.Type.Edge_3],
    (2, 4)  : [Topology.Type.Quadrilateral],
    (2, 6)  : [Topology.Type.Triangle_6],
    (2, 8)  : [Topology.Type.Quadrilateral_8],
    (3, 1)  : [Topology.Type.Polyvertex],
    (3, 2)  : [Topology.Type.Polyline],
    (3, 3)  : [Topology.Type.Triangle, Topology.Type.Edge_3],
    (3, 4)  : [Topology.Type.Quadrilateral, Topology.Type.Tetrahedron],
    (3, 5)  : [Topology.Type.Pyramid],
    (3, 6)  : [Topology.Type.Triangle_6, Topology.Type.Wedge],
    (3, 8)  : [Topology.Type.Hexahedron, Topology.Type.Quadrilateral_8],
    (3, 10) : [Topology.Type.Tetrahedron_10],
    (3, 13) : [Topology.Type.Pyramid_13],
    (3, 15) : [Topology.Type.Wedge_15],
    (3, 20) : [Topology.Type.Hexahedron_20]
}



def __ParseCellType(cell_name: str) -> Topology.Type:
    regex = re.compile(R"(\w+)([123])d([1-9][0-9]*)n")
    regex_match = regex.match(cell_name.lower())

    if not regex_match:
        raise RuntimeError(f"failed to parse cell type '{cell_name}'")

    dimensions = int(regex_match.group(2))
    nodes = int(regex_match.group(3))
    cell_id = (dimensions, nodes)
    topology_candidates: "list[Topology.Type]" = __CELL_MAP.get(cell_id, [])

    if not topology_candidates:
        raise RuntimeError(f"unrecognized geometry: {cell_name}")
    elif len(topology_candidates) == 1:
        return topology_candidates[0]
    else:
        # Handle special ambiguous cases
        geometry_name_lower = regex_match.group(1)
        topology_type: Optional[Topology.Type] = None

        # Case (2, 3)
        # Decide whether the geometry refers to
        # - linear triangle
        # - quadratic line
        if cell_id == (2, 3) or cell_id == (3, 3):
            if "line" in geometry_name_lower:
                topology_type = next((t for t in topology_candidates if "line" in t.name.lower()), None)
                if topology_type is not None:
                    return topology_type
            elif "triangle" in geometry_name_lower:
                topology_type = next((t for t in topology_candidates if "triangle" in t.name.lower()), None)
                if topology_type is not None:
                    return topology_type

        # Case (3, 4)
        # Decide whether the geometry refers to
        # - linear quadrilateral
        # - linear tetrahedron
        elif cell_id == (3, 4):
            if "tetrahedron" in geometry_name_lower or "tetrahedra" in geometry_name_lower:
                topology_type = next((t for t in topology_candidates if "tetrahedron" in t.name.lower()), None)
                if topology_type is not None:
                    return topology_type
            elif "quadrilateral" in geometry_name_lower or "rectangle" in geometry_name_lower:
                topology_type = next((t for t in topology_candidates if "quadrilateral" in t.name.lower()), None)
                if topology_type is not None:
                    return topology_type

        # Case (3, 6)
        # Decide whether the geometry refers to
        # - quadratic triangle
        # - linear wedge
        elif cell_id == (3, 6):
            if "triangle" in geometry_name_lower:
                topology_type = next((t for t in topology_candidates if "triangle" in t.name.lower()), None)
                if topology_type is not None:
                    return topology_type
            elif "wedge" in geometry_name_lower:
                topology_type = next((t for t in topology_candidates if "wedge" in t.name.lower()), None)
                if topology_type is not None:
                    return topology_type

        # Case (3, 8)
        # Decide whether the geometry refers to
        # - quadratic quadrilateral
        # - linear hexahedron
        elif cell_id == (3, 8):
            if "hexahedron" in geometry_name_lower or "hexahedra" in geometry_name_lower:
                topology_type = next((t for t in topology_candidates if "hexahedron" in t.name.lower()), None)
                if topology_type is not None:
                    return topology_type
            if "quadrilateral" in geometry_name_lower or "rectangle" in geometry_name_lower:
                topology_type = next((t for t in topology_candidates if "quadrilateral" in t.name.lower()), None)
                if topology_type is not None:
                    return topology_type

        raise RuntimeError(f"ambiguous geometry type: {cell_name}")

    # The program should not reach this point
    raise RuntimeError("unhandled geometry type: {cell_name}")



def __ParseCellGroup(cell_name: str,
                     path: h5py.Group,
                     node_coordinate_set: DataItem,
                     grid: Grid,
                     root_cell_data: "Optional[dict[str,DataItem]]" = None) -> DataItem:
    # @todo @matekelemen
    if root_cell_data is None:
        cell_grid = GridLeaf(cell_name)

        # Parse topology
        connectivity_set: h5py.Dataset = path["Connectivities"]
        topology = Topology(__ParseCellType(cell_name), connectivity_set.shape[0])
        topology_data = LeafDataItem(HDF5Data(
            Double(),
            connectivity_set.shape,
            pathlib.Path(connectivity_set.file.filename),
            connectivity_set.name
        ))
        topology.append(topology_data)
        cell_grid.append(topology)

        # Add node coordinates
        geometry = Geometry(Geometry.Type.XYZ)
        geometry.append(node_coordinate_set)
        cell_grid.append(geometry)

        grid.append(cell_grid)
        return topology_data
    else:
        pass



def __ParseCellGroups(path: h5py.Group,
                      node_coordinate_set: DataItem,
                      grid: Grid,
                      root_cell_data: "Optional[dict[str,DataItem]]" = None) -> "dict[str,DataItem]":
    output: "dict[str,DataItem]" = {}
    for name, cell_group in path.items():
        if isinstance(cell_group, h5py.Group):
            output[name] = __ParseCellGroup(name,
                                            cell_group,
                                            node_coordinate_set,
                                            grid,
                                            root_cell_data = root_cell_data)
    return output



class __ParentElements:

    def __init__(self,
                 node_coordinate_data: DataItem,
                 node_index_data: DataItem,
                 element_data: "dict[str,DataItem]",
                 condition_data: "dict[str,DataItem]") -> None:
        self.node_coordinate_data = node_coordinate_data
        self.node_index_data = node_index_data
        self.element_data = element_data
        self.condition_data = condition_data



class SubgroupNaming(Enum):
    Default     = 0
    Paraview    = 1



def ParseRootMesh(path: h5py.Group,
                  name: str = "RootModelPart",
                  subgroup_naming: SubgroupNaming = SubgroupNaming.Paraview) -> Grid:
    grid: Grid = GridTree(name)

    # Parse nodes
    node_grid = GridLeaf("Nodes")

    if not "Nodes" in path:
        raise RuntimeError(f"no Nodes found in {path}")

    node_group: h5py.Group = path["Nodes"]
    if not isinstance(node_group, h5py.Group):
        raise RuntimeError(f"Nodes is expected to be a group, but is a {type(path['Nodes'])}")

    # Parse node coordinates
    node_coordinate_set: h5py.Dataset = node_group["Local"]["Coordinates"]
    node_coordinate_data = LeafDataItem(HDF5Data(
        Double(),
        node_coordinate_set.shape,
        pathlib.Path(node_coordinate_set.file.filename),
        node_coordinate_set.name
    ))

    node_geometry = Geometry(Geometry.Type.XYZ)
    node_geometry.append(node_coordinate_data)
    node_grid.append(node_geometry)

    # Add default topology: point cloud
    point_cloud_topology = Topology(Topology.Type.Polyvertex, node_coordinate_set.shape[0])
    node_indices: h5py.Dataset = path["Xdmf"]["Nodes"]["Indices"]
    node_index_data = LeafDataItem(HDF5Data(
        Int(),
        node_indices.shape,
        pathlib.Path(node_indices.file.filename),
        node_indices.name
    ))
    point_cloud_topology.append(node_index_data)
    node_grid.append(point_cloud_topology)

    # Parse node IDs
    node_ids: h5py.Dataset = node_group["Local"]["Ids"]
    node_id_attribute = NodeAttribute("NodeID", LeafDataItem(HDF5Data(
        Int(),
        node_ids.shape,
        pathlib.Path(node_ids.file.filename),
        node_ids.name
    )))
    node_grid.append(node_id_attribute)

    grid.append(node_grid)

    # Parse elements and conditions
    element_data: "dict[str,DataItem]" = {}
    condition_data: "dict[str,DataItem]" = {}
    xdmf_group: h5py.Group = path["Xdmf"]

    element_groups: Optional[h5py.Group] = xdmf_group.get("Elements", None)
    if element_groups is not None:
        element_data.update(__ParseCellGroups(element_groups, node_coordinate_data, grid))

    condition_groups: Optional[h5py.Group] = xdmf_group.get("Conditions", None)
    if condition_groups is not None:
        condition_data.update(__ParseCellGroups(condition_groups, node_coordinate_data, grid))

    # Parse sub model parts
    sub_groups: Optional[h5py.Group] = xdmf_group.get("SubModelParts", None)
    if sub_groups is not None:
        root_elements = __ParentElements(node_coordinate_data,
                                         node_index_data,
                                         element_data,
                                         condition_data)
        for name, sub_group in sub_groups.items():
            grid.append(ParseMesh(sub_group,
                                  name = name,
                                  parent_elements = root_elements,
                                  subgroup_naming = subgroup_naming))

    return grid



def ParseMesh(path: h5py.Group,
              name: str = "RootModelPart",
              parent_elements: Optional[__ParentElements] = None,
              subgroup_naming: SubgroupNaming = SubgroupNaming.Paraview) -> Grid:
    """ @brief Parse a mesh corresponding to a @ref Kratos::ModelPart "model part".
        @arg name name of the model part.
        @arg path group in the HDF5 file pointing at the root of the model part.
        @details This assumes that at least the following groups are present in
                 the provided path:
                 - Nodes
                 - Xdmf
                 "Nodes" must contain the IDs and coordinates of all nodes in the mesh,
                 while "Xdmf" must contain "NodeIDMap".
    """
    if parent_elements is None:
        return ParseRootMesh(path, name = name)
    else:
        grid_tree: Grid = GridTree(name)

        # Add point cloud if the subgroup contains nodes
        node_group: Optional[h5py.Group] = path.get("Nodes", None)
        if node_group is not None:
            node_subgroup_name = f"{name}.Nodes" if subgroup_naming == SubgroupNaming.Paraview else "Nodes"
            node_grid: Grid = GridLeaf(node_subgroup_name)

            # Point cloud topology
            node_index_set: h5py.Dataset = node_group["Indices"]
            node_indices = LeafDataItem(HDF5Data(Int(),
                                                 node_index_set.shape,
                                                 pathlib.Path(node_index_set.file.filename),
                                                 node_index_set.name))
            point_cloud_topology = Topology(Topology.Type.Polyvertex, node_index_set.shape[0])
            point_cloud_topology.append(CoordinateDataItem(node_indices, parent_elements.node_index_data))
            node_grid.append(point_cloud_topology)

            # Point cloud geometry
            node_geometry = Geometry(Geometry.Type.XYZ)
            node_geometry.append(parent_elements.node_coordinate_data)
            node_grid.append(node_geometry)

            grid_tree.append(node_grid)

            # Add elements if the subgroup contains elements
            for cell_type, cell_data in (("Elements", parent_elements.element_data),
                                         ("Conditions", parent_elements.condition_data)):
                element_groups: Optional[h5py.Group] = path.get(cell_type, None)
                if element_groups is not None:
                    for cell_name, element_group in element_groups.items():
                        cell_subgroup_name = f"{name}.{cell_name}" if subgroup_naming == SubgroupNaming.Paraview else cell_name
                        cell_grid = GridLeaf(cell_subgroup_name)

                        cell_index_set: h5py.Dataset = element_group["Indices"]
                        topology_type = __ParseCellType(cell_name)
                        cell_topology = Topology(topology_type, cell_index_set.shape[0])
                        cell_topology.append(CoordinateDataItem(
                            LeafDataItem(HDF5Data(Int(),
                                                cell_index_set.shape,
                                                pathlib.Path(cell_index_set.file.filename),
                                                cell_index_set.name)),
                            cell_data[cell_name]
                        ))

                        cell_grid.append(cell_topology)
                        cell_grid.append(node_geometry)
                        grid_tree.append(cell_grid)

        subgroups: Optional[h5py.Group] = path.get("SubModelParts", None)
        if subgroups is not None:
            for subgroup_name, subgroup in subgroups.items():
                if subgroup_naming == SubgroupNaming.Paraview:
                    subgroup_name = f"{name}/{subgroup_name}"
                ParseMesh(subgroup,
                          subgroup_name,
                          parent_elements = parent_elements,
                          subgroup_naming = subgroup_naming)

        return grid_tree





