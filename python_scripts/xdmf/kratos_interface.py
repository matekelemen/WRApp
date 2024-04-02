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
from KratosMultiphysics.WRApplication.xdmf.Data import HDF5Data
from KratosMultiphysics.WRApplication.xdmf.DataItem import DataItem, LeafDataItem, CoordinateDataItem
from KratosMultiphysics.WRApplication.xdmf.Attribute import Attribute
from KratosMultiphysics.WRApplication.xdmf.Topology import Topology
from KratosMultiphysics.WRApplication.xdmf.Geometry import Geometry
from KratosMultiphysics.WRApplication.xdmf.Grid import Grid, GridTree, GridLeaf

# --- STD Imports ---
from typing import Optional
import re
from enum import Enum



def __MakeAttribute(root_attribute_set: DataItem,
                    attribute_name: str,
                    attribute_center: Attribute.Center,
                    cell_index_set: Optional[DataItem] = None) -> Attribute:
    attribute_set: DataItem
    if cell_index_set is None:
        attribute_set = root_attribute_set
    else:
        attribute_set = CoordinateDataItem(cell_index_set, root_attribute_set)

    attribute = Attribute(attribute_name, attribute_center)
    attribute.append(attribute_set)
    return attribute



def __ParseAttribute(path: h5py.Dataset,
                     center: Attribute.Center,
                     cell_index_set: Optional[DataItem] = None) -> Attribute:
    name: str = path.name[len(path.parent.name) + 1:]
    root_set = LeafDataItem(HDF5Data.FromDataset(path))
    return __MakeAttribute(root_set, name, center, cell_index_set = cell_index_set)



def __ParseAttributeGroup(path: h5py.Group,
                          center: Attribute.Center,
                          cell_index_set: Optional[DataItem] = None) -> "dict[str,Attribute]":
    attribute_sets: "dict[str,Attribute]" = {}
    for name, group in path.items():
        attribute = __ParseAttribute(group,
                                     center,
                                     cell_index_set = cell_index_set)
        attribute_sets[name] = attribute
    return attribute_sets



__CELL_MAP : "dict[tuple[int,int],list[Topology.Type]]" = {
    (2, 1)  : [Topology.Type.Polyvertex],
    (2, 2)  : [Topology.Type.Polyline],
    (2, 3)  : [Topology.Type.Edge_3, Topology.Type.Triangle],
    (2, 4)  : [Topology.Type.Quadrilateral],
    (2, 6)  : [Topology.Type.Triangle_6],
    (2, 8)  : [Topology.Type.Quadrilateral_8],
    (3, 1)  : [Topology.Type.Polyvertex],
    (3, 2)  : [Topology.Type.Polyline],
    (3, 3)  : [Topology.Type.Edge_3, Topology.Type.Triangle],
    (3, 4)  : [Topology.Type.Quadrilateral, Topology.Type.Tetrahedron],
    (3, 5)  : [Topology.Type.Pyramid],
    (3, 6)  : [Topology.Type.Triangle_6, Topology.Type.Wedge],
    (3, 8)  : [Topology.Type.Quadrilateral_8, Topology.Type.Hexahedron],
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
        if cell_id == (2, 3):
            if "line" in geometry_name_lower:
                topology_type = next((t for t in topology_candidates if "line" in t.name.lower()), None)
                if topology_type is not None:
                    return topology_type
            elif "triangle" in geometry_name_lower:
                topology_type = next((t for t in topology_candidates if "triangle" in t.name.lower()), None)
                if topology_type is not None:
                    return topology_type
            elif "condition" in geometry_name_lower: # <== a condition always refers to an object with 1 dimension less
                topology_type = topology_candidates[0]
                if topology_type is not None:
                    return topology_type

        # Case (3, 3)
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
            elif "condition" in geometry_name_lower: # <== a condition always refers to an object with 1 dimension less
                topology_type = topology_candidates[1]
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
            elif "condition" in geometry_name_lower: # <== a condition always refers to an object with 1 dimension less
                topology_type = topology_candidates[0]
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
            elif "condition" in geometry_name_lower: # <== a condition always refers to an object with 1 dimension less
                topology_type = topology_candidates[0]
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
            elif "condition" in geometry_name_lower: # <== a condition always refers to an object with 1 dimension less
                topology_type = topology_candidates[0]
                if topology_type is not None:
                    return topology_type

        raise RuntimeError(f"ambiguous geometry type: {cell_name}")

    # The program should not reach this point
    raise RuntimeError("unhandled geometry type: {cell_name}")



def __ParseCellGroup(cell_name: str,
                     path: h5py.Group,
                     node_coordinate_set: DataItem,
                     attribute_paths: "list[h5py.Group]",
                     grid: Grid,
                     root_cell_data: "Optional[dict[str,DataItem]]" = None) -> "tuple[DataItem,DataItem]":
    cell_grid = GridLeaf(cell_name)

    # Parse topology
    topology = Topology(__ParseCellType(cell_name))
    topology_data: DataItem
    cell_indices: Optional[DataItem] = None
    if root_cell_data is None:
        connectivity_set: h5py.Dataset = path["Connectivities"]
        topology_data = LeafDataItem(HDF5Data.FromDataset(connectivity_set))
    else:
        cell_ids = LeafDataItem(HDF5Data.FromDataset(path["Ids"]))
        cell_indices = CoordinateDataItem()
        topology_data = CoordinateDataItem(cell_indices, root_cell_data[cell_name])
    topology.append(topology_data)
    cell_grid.append(topology)

    # Add node coordinates
    geometry = Geometry(Geometry.Type.XYZ)
    geometry.append(node_coordinate_set)
    cell_grid.append(geometry)

    # Parse attributes
    for attribute_path in attribute_paths:
        for attribute in __ParseAttributeGroup(attribute_path,
                                               Attribute.Center.Cell,
                                               cell_index_set = cell_indices).values():
            cell_grid.append(attribute)

    grid.append(cell_grid)

    return topology_data, LeafDataItem(HDF5Data.FromDataset(path["IdMap"]))



def __ParseCellGroups(path: h5py.Group,
                      node_coordinate_set: DataItem,
                      attribute_paths: "list[h5py.Group]",
                      grid: Grid,
                      root_cell_data: "Optional[dict[str,DataItem]]" = None) -> "dict[str,tuple[DataItem,DataItem]]":
    output: "dict[str,tuple[DataItem,DataItem]]" = {}
    for name, cell_group in path.items():
        if isinstance(cell_group, h5py.Group):
            output[name] = __ParseCellGroup(name,
                                            cell_group,
                                            node_coordinate_set,
                                            attribute_paths,
                                            grid,
                                            root_cell_data = root_cell_data)
    return output



class __ParentElements:

    def __init__(self,
                 node_coordinate_data: DataItem,
                 node_id_map: DataItem,
                 node_index_data: DataItem,
                 element_data: "dict[str,tuple[DataItem,DataItem]]",
                 condition_data: "dict[str,tuple[DataItem,DataItem]]") -> None:
        self.node_coordinate_data = node_coordinate_data
        self.node_id_map = node_id_map
        self.node_index_data = node_index_data
        self.element_data = element_data
        self.condition_data = condition_data



class SubgroupNaming(Enum):
    Default     = 0
    Paraview    = 1



def ParseRootMesh(path: h5py.Group,
                  name: str = "RootModelPart",
                  attribute_path: Optional[h5py.Group] = None,
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
    node_coordinate_data = LeafDataItem(HDF5Data.FromDataset(node_coordinate_set))
    node_geometry = Geometry(Geometry.Type.XYZ)
    node_geometry.append(node_coordinate_data)
    node_grid.append(node_geometry)

    # Add default topology: point cloud
    point_cloud_topology = Topology(Topology.Type.Polyvertex)
    node_indices: h5py.Dataset = path["Xdmf"]["Nodes"]["Indices"]
    node_index_data = LeafDataItem(HDF5Data.FromDataset(node_indices))
    point_cloud_topology.append(node_index_data)
    node_grid.append(point_cloud_topology)

    # Parse node IDs
    node_ids: h5py.Dataset = node_group["Local"]["Ids"]
    node_id_attribute = Attribute("NodeID", Attribute.Center.Node)
    node_id_attribute.append(LeafDataItem(HDF5Data.FromDataset(node_ids)))
    node_grid.append(node_id_attribute)

    grid.append(node_grid)

    # Parse elements and conditions
    element_data: "dict[str,tuple[DataItem,DataItem]]" = {}
    condition_data: "dict[str,tuple[DataItem,DataItem]]" = {}
    xdmf_group: h5py.Group = path["Xdmf"]

    element_groups: Optional[h5py.Group] = xdmf_group.get("Elements", None)
    if element_groups is not None:
        attribute_paths: "list[h5py.Group]" = []
        if attribute_path is not None:
            for attribute_group_name in ("ElementDataValues", "ElementFlagValues"):
                attribute_group: Optional[h5py.Group] = attribute_path.get(attribute_group_name, None)
                if attribute_group is not None:
                    attribute_paths.append(attribute_group)

        element_data.update(__ParseCellGroups(element_groups,
                                              node_coordinate_data,
                                              attribute_paths,
                                              grid))

    condition_groups: Optional[h5py.Group] = xdmf_group.get("Conditions", None)
    if condition_groups is not None:
        attribute_paths: "list[h5py.Group]" = []
        if attribute_path is not None:
            for attribute_group_name in ("ConditionDataValues", "ConditionFlagValues"):
                attribute_group: Optional[h5py.Group] = attribute_path.get(attribute_group_name, None)
                if attribute_group is not None:
                    attribute_paths.append(attribute_group)

        condition_data.update(__ParseCellGroups(condition_groups,
                                                node_coordinate_data,
                                                attribute_paths,
                                                grid))

    # Parse sub model parts
    sub_groups: Optional[h5py.Group] = xdmf_group.get("SubModelParts", None)
    if sub_groups is not None:
        node_id_map = LeafDataItem(HDF5Data.FromDataset(path["Xdmf"]["Nodes"]["IdMap"]))
        root_elements = __ParentElements(node_coordinate_data,
                                         node_id_map,
                                         node_index_data,
                                         element_data,
                                         condition_data)
        for name, sub_group in sub_groups.items():
            grid.append(ParseMesh(sub_group,
                                  name = name,
                                  parent_elements = root_elements,
                                  attribute_path = attribute_path,
                                  subgroup_naming = subgroup_naming))

    return grid



def ParseSubmesh(path: h5py.Group,
                 name: str,
                 parent_elements: __ParentElements,
                 attribute_path: Optional[h5py.Group] = None,
                 subgroup_naming: SubgroupNaming = SubgroupNaming.Paraview) -> Grid:
    grid_tree: Grid = GridTree(name)

    # Add point cloud if the subgroup contains nodes
    node_group: Optional[h5py.Group] = path.get("Nodes", None)
    if node_group is not None:
        node_subgroup_name = f"{name}.Nodes" if subgroup_naming == SubgroupNaming.Paraview else "Nodes"
        node_grid: Grid = GridLeaf(node_subgroup_name)

        # Point cloud topology
        node_id_set: h5py.Dataset = node_group["Ids"]
        node_ids = LeafDataItem(HDF5Data.FromDataset(node_id_set))
        node_indices = CoordinateDataItem(node_ids, parent_elements.node_id_map)
        point_cloud_topology = Topology(Topology.Type.Polyvertex)
        point_cloud_topology.append(CoordinateDataItem(node_indices, parent_elements.node_index_data))
        node_grid.append(point_cloud_topology)

        # Point cloud geometry
        node_geometry = Geometry(Geometry.Type.XYZ)
        node_geometry.append(parent_elements.node_coordinate_data)
        node_grid.append(node_geometry)

        grid_tree.append(node_grid)

        # Add elements and conditions if the subgroup contains them
        for cell_type, cell_data, attribute_group_names in (("Elements", parent_elements.element_data, ("ElementDataValues", "ElementFlagValues")),
                                                            ("Conditions", parent_elements.condition_data, ("ConditionDataValues", "ConditionFlagValues"))):
            cell_groups: Optional[h5py.Group] = path.get(cell_type, None)
            if cell_groups is not None:
                for cell_name, cell_group in cell_groups.items():
                    # Add the mesh to the current grid level
                    cell_subgroup_name = f"{name}.{cell_name}" if subgroup_naming == SubgroupNaming.Paraview else cell_name
                    cell_grid = GridLeaf(cell_subgroup_name)

                    cell_id_set = LeafDataItem(HDF5Data.FromDataset(cell_group["Ids"]))
                    cell_index_set = CoordinateDataItem(cell_id_set, cell_data[cell_name][1])
                    topology_type = __ParseCellType(cell_name)
                    cell_topology = Topology(topology_type)
                    cell_topology.append(CoordinateDataItem(cell_index_set, cell_data[cell_name][0]))

                    cell_grid.append(cell_topology)
                    cell_grid.append(node_geometry)

                    # Add attributes to the current grid level
                    if attribute_path is not None:
                        for attribute_group_name in attribute_group_names:
                            attribute_group: Optional[h5py.Group] = attribute_path.get(attribute_group_name, None)
                            if attribute_group is not None:
                                for attribute in __ParseAttributeGroup(attribute_group,
                                                                       Attribute.Center.Cell,
                                                                       cell_index_set = cell_index_set).values():
                                    cell_grid.append(attribute)

                    # Insert the current grid level into the grid tree
                    grid_tree.append(cell_grid)

    subgroups: Optional[h5py.Group] = path.get("SubModelParts", None)
    if subgroups is not None:
        for subgroup_name, subgroup in subgroups.items():
            if subgroup_naming == SubgroupNaming.Paraview:
                subgroup_name = f"{name}/{subgroup_name}"
            ParseMesh(subgroup,
                      subgroup_name,
                      parent_elements = parent_elements,
                      attribute_path = attribute_path,
                      subgroup_naming = subgroup_naming)

    return grid_tree



def ParseMesh(path: h5py.Group,
              name: str = "RootModelPart",
              attribute_path: Optional[h5py.Group] = None,
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
    attribute_path = None
    if parent_elements is None:
        return ParseRootMesh(path,
                             name = name,
                             attribute_path = attribute_path,
                             subgroup_naming = subgroup_naming)
    else:
        return ParseSubmesh(path,
                            name,
                            parent_elements,
                            attribute_path = attribute_path,
                            subgroup_naming = subgroup_naming)





