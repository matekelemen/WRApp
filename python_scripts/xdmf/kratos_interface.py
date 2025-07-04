""" @author Máté Kelemen"""

# --- External Imports ---
#try:
#    import h5py
#except ModuleNotFoundError:
#    class h5py:
#        class Group: pass
#        class Dataset: pass
import h5py

# --- WRApp Imports ---
from KratosMultiphysics.WRApplication.xdmf.Data import HDF5Data
from KratosMultiphysics.WRApplication.xdmf.DataItem import DataItem, LeafDataItem, CoordinateDataItem, MakeCoordinateSlice
from KratosMultiphysics.WRApplication.xdmf.Attribute import Attribute
from KratosMultiphysics.WRApplication.xdmf.Topology import Topology
from KratosMultiphysics.WRApplication.xdmf.Geometry import Geometry
from KratosMultiphysics.WRApplication.xdmf.Grid import Grid, GridLeaf, GridCollection
from KratosMultiphysics.WRApplication.xdmf.Time import TimePoint

# --- STD Imports ---
from typing import Optional, Union
import re
from enum import Enum



def __TimeStamp(grid: Grid, time: Union[int,float,None]) -> None:
    if time is not None:
        grid.append(TimePoint(time))



def __MakeAttribute(root_attribute_set: DataItem,
                    attribute_name: str,
                    attribute_center: Attribute.Center,
                    index_set: Optional[DataItem] = None) -> Optional[Attribute]:
    if attribute_name != "_partition": # <== not something we care about
        attribute_set: Optional[DataItem] = None

        if index_set is None:
            attribute_set = root_attribute_set
        else:
            component_indices: "list[int]" = []
            attribute_shape = root_attribute_set.GetShape()
            if 1 < len(attribute_shape):
                component_indices = list(range(root_attribute_set.GetShape()[1]))
            attribute_set = MakeCoordinateSlice(index_set,
                                                root_attribute_set,
                                                component_indices)

        if attribute_set is not None:
            attribute = Attribute(attribute_name, attribute_center)
            attribute.append(attribute_set)
            return attribute



def __ParseAttribute(path: h5py.Dataset,
                     center: Attribute.Center,
                     index_set: Optional[DataItem] = None) -> Optional[Attribute]:
    name: str = path.name[len(path.parent.name) + 1:]
    root_set = LeafDataItem(HDF5Data.FromDataset(path))
    return __MakeAttribute(root_set, name, center, index_set = index_set)



def __ParseAttributeGroup(path: h5py.Group,
                          center: Attribute.Center,
                          index_set: Optional[DataItem] = None) -> "dict[str,Attribute]":
    attribute_sets: "dict[str,Attribute]" = {}
    for name, group in path.items():
        maybe_attribute = __ParseAttribute(group,
                                           center,
                                           index_set = index_set)
        if maybe_attribute is not None:
            attribute_sets[name] = maybe_attribute
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



def __ParseCellType(cell_name: str, nodes_per_element: int) -> Topology.Type:
    regex = re.compile(R"(\w+)([123])d([1-9][0-9]*)n")
    regex_match = regex.match(cell_name.lower())

    if not regex_match:
        # All terrible names from here: there's no reference to their
        # geometry at all.

        # VMS fluid elements
        # This one's relatively simple because it leaks info
        # about its dimension at least. Also, there's no point to
        # quadratic lines for a fluid element, so it's not ambiguous.
        if cell_name == "VMS2D":
            if nodes_per_element == 3:
                return Topology.Type.Triangle
            elif nodes_per_element == 4:
                return Topology.Type.Quadrilateral
            elif nodes_per_element == 6:
                return Topology.Type.Triangle_6
            elif nodes_per_element == 8:
                return Topology.Type.Quadrilateral_8

        # 2D conditions (e.g.: MonolithicWallCondition2D)
        # The usual confusing business with Kratos conditions:
        # the geometry is 1 dimension less than what the name indicates.
        if cell_name.lower().endswith("condition2d"):
            if nodes_per_element == 2:
                return Topology.Type.Polyline
            elif nodes_per_element == 2:
                return Topology.Type.Edge_3

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
            elif "element" in geometry_name_lower: # <== elements always refer to an object with the same dimensionality
                return topology_candidates[1]

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
                return topology_candidates[0]
            elif "element" in geometry_name_lower: # <== elements always refer to an object with the same dimensionality
                return topology_candidates[1]

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
                     id_set: DataItem,
                     attribute_paths: "list[h5py.Group]",
                     node_attributes: "dict[str,Attribute]",
                     grid: Grid,
                     time: Optional[Union[int,float]] = None) -> "tuple[DataItem,DataItem]":
    cell_grid = GridLeaf(cell_name)
    __TimeStamp(cell_grid, time)

    # Parse topology
    connectivity_set: h5py.Dataset = path["Connectivities"]
    topology = Topology(__ParseCellType(cell_name, connectivity_set.shape[1]))
    topology_data = LeafDataItem(HDF5Data.FromDataset(connectivity_set))
    topology.append(topology_data)
    cell_grid.append(topology)

    # Add node coordinates
    geometry = Geometry(Geometry.Type.XYZ)
    geometry.append(node_coordinate_set)
    cell_grid.append(geometry)

    # Parse cell attributes
    cell_indices = LeafDataItem(HDF5Data.FromDataset(path["Indices"]))
    for attribute_path in attribute_paths:
        for attribute in __ParseAttributeGroup(attribute_path,
                                               Attribute.Center.Cell,
                                               index_set = cell_indices).values():
            cell_grid.append(attribute)

    # Add cell IDs as attributes
    id_attribute = Attribute("ID", Attribute.Center.Cell)
    id_attribute.append(CoordinateDataItem(cell_indices, id_set))
    cell_grid.append(id_attribute)

    # Add node attributes
    for attribute in node_attributes.values():
        cell_grid.append(attribute)

    grid.append(cell_grid)

    return topology_data, cell_indices



def __ParseCellGroups(path: h5py.Group,
                      node_coordinate_set: DataItem,
                      id_set: DataItem,
                      attribute_paths: "list[h5py.Group]",
                      node_attributes: "dict[str,Attribute]",
                      grid: Grid,
                      time: Optional[Union[int,float]] = None) -> "tuple[dict[str,DataItem],dict[str,DataItem]]":
    topologies: "dict[str,DataItem]" = {}
    index_maps: "dict[str,DataItem]" = {}
    for name, cell_group in path.items():
        if isinstance(cell_group, h5py.Group):
            topology, index_map = __ParseCellGroup(
                name,
                cell_group,
                node_coordinate_set,
                id_set,
                attribute_paths,
                node_attributes,
                grid,
                time = time)
            topologies[name] = topology
            index_maps[name] = index_map
    return topologies, index_maps



class __RootData:

    def __init__(self,
                 node_coordinate_data: DataItem,
                 node_ids: DataItem,
                 element_topologies: "dict[str,DataItem]",
                 element_index_maps: "dict[str,DataItem]",
                 element_ids: DataItem,
                 condition_topologies: "dict[str,DataItem]",
                 condition_index_maps: "dict[str,DataItem]",
                 condition_ids: DataItem) -> None:
        self.node_coordinate_data = node_coordinate_data
        self.node_ids = node_ids
        self.element_topologies = element_topologies
        self.element_index_maps = element_index_maps
        self.element_ids = element_ids
        self.condition_topologies = condition_topologies
        self.condition_index_maps = condition_index_maps
        self.condition_ids = condition_ids



class SubgroupNaming(Enum):
    Default     = 0
    Paraview    = 1



def ParseRootMesh(path: h5py.Group,
                  name: str = "RootModelPart",
                  attribute_path: Optional[h5py.Group] = None,
                  time: Optional[Union[int,float]] = None,
                  subgroup_naming: SubgroupNaming = SubgroupNaming.Paraview) -> Grid:
    grid: Grid = GridCollection(name, GridCollection.Type.Spatial)
    __TimeStamp(grid, time)

    # Parse nodes
    node_grid = GridLeaf("Nodes")
    __TimeStamp(node_grid, time)

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
    node_indices = LeafDataItem(HDF5Data.FromDataset(path["Xdmf"]["Nodes"]["Indices"]))
    point_cloud_topology.append(node_indices)
    node_grid.append(point_cloud_topology)

    # Parse node IDs
    node_ids = LeafDataItem(HDF5Data.FromDataset(node_group["Local"]["Ids"]))
    node_id_attribute = Attribute("ID", Attribute.Center.Node)
    node_id_attribute.append(node_ids)
    node_grid.append(node_id_attribute)

    # Parse node attributes
    node_attributes: "dict[str,Attribute]" = {}
    if attribute_path is not None:
        for attribute_group_name in ("NodalSolutionStepData",
                                     "NodalDataValues",
                                     "NodalFlagValues"):
            attribute_group: Optional[h5py.Group] = attribute_path.get(attribute_group_name, None)
            if attribute_group is not None:
                node_attributes.update(__ParseAttributeGroup(attribute_group, Attribute.Center.Node))

    for attribute in node_attributes.values():
        node_grid.append(attribute)

    grid.append(node_grid)

    # Parse elements and conditions
    element_topologies: "dict[str,DataItem]" = {}
    element_index_maps: "dict[str,DataItem]" = {}
    element_ids: DataItem
    condition_topologies: "dict[str,DataItem]" = {}
    condition_index_maps: "dict[str,DataItem]" = {}
    condition_ids: DataItem
    xdmf_group: h5py.Group = path["Xdmf"]

    element_groups: Optional[h5py.Group] = xdmf_group.get("Elements", None)
    if element_groups is not None:
        element_ids = LeafDataItem(HDF5Data.FromDataset(element_groups["Ids"]))

        attribute_paths: "list[h5py.Group]" = []
        if attribute_path is not None:
            for attribute_group_name in ("ElementDataValues", "ElementFlagValues"):
                attribute_group: Optional[h5py.Group] = attribute_path.get(attribute_group_name, None)
                if attribute_group is not None:
                    attribute_paths.append(attribute_group)

        topologies, index_maps = __ParseCellGroups(
            element_groups,
            node_coordinate_data,
            element_ids,
            attribute_paths,
            node_attributes,
            grid,
            time = time)
        element_topologies.update(topologies)
        element_index_maps.update(index_maps)

    condition_groups: Optional[h5py.Group] = xdmf_group.get("Conditions", None)
    if condition_groups is not None:
        condition_ids = LeafDataItem(HDF5Data.FromDataset(condition_groups["Ids"]))

        attribute_paths: "list[h5py.Group]" = []
        if attribute_path is not None:
            for attribute_group_name in ("ConditionDataValues", "ConditionFlagValues"):
                attribute_group: Optional[h5py.Group] = attribute_path.get(attribute_group_name, None)
                if attribute_group is not None:
                    attribute_paths.append(attribute_group)

        topologies, index_maps = __ParseCellGroups(
            condition_groups,
            node_coordinate_data,
            condition_ids,
            attribute_paths,
            node_attributes,
            grid)
        condition_topologies.update(topologies)
        condition_index_maps.update(index_maps)

    # Parse sub model parts
    sub_groups: Optional[h5py.Group] = xdmf_group.get("SubModelParts", None)
    if sub_groups is not None:
        root_data = __RootData(node_coordinate_data,
                               node_ids,
                               element_topologies,
                               element_index_maps,
                               element_ids,
                               condition_topologies,
                               condition_index_maps,
                               condition_ids)
        for name, sub_group in sub_groups.items():
            grid.append(ParseMesh(sub_group,
                                  name = name,
                                  root_data = root_data,
                                  attribute_path = attribute_path,
                                  time = time,
                                  subgroup_naming = subgroup_naming))

    return grid



def ParseSubmesh(path: h5py.Group,
                 name: str,
                 root_data: __RootData,
                 time: Optional[Union[int,float]] = None,
                 attribute_path: Optional[h5py.Group] = None,
                 subgroup_naming: SubgroupNaming = SubgroupNaming.Paraview) -> Grid:
    grid_tree: Grid = GridCollection(name, GridCollection.Type.Spatial)
    __TimeStamp(grid_tree, time)

    # Add point cloud if the subgroup contains nodes
    node_group: Optional[h5py.Group] = path.get("Nodes", None)
    if node_group is not None:
        node_subgroup_name = f"{name}.Nodes" if subgroup_naming == SubgroupNaming.Paraview else "Nodes"
        node_grid: Grid = GridLeaf(node_subgroup_name)
        __TimeStamp(node_grid, time)

        # Point cloud topology
        node_index_set: h5py.Dataset = node_group["Indices"]
        node_indices = LeafDataItem(HDF5Data.FromDataset(node_index_set))
        point_cloud_topology = Topology(Topology.Type.Polyvertex)
        point_cloud_topology.append(node_indices)
        node_grid.append(point_cloud_topology)

        # Point cloud geometry
        node_geometry = Geometry(Geometry.Type.XYZ)
        node_geometry.append(root_data.node_coordinate_data)
        node_grid.append(node_geometry)

        # Parse node attributes
        node_attributes: "dict[str,Attribute]" = {}
        if attribute_path is not None:
            for attribute_group_name in ("NodalSolutionStepData",
                                         "NodalDataValues",
                                         "NodalFlagValues"):
                attribute_group: "Optional[h5py.Group]" = attribute_path.get(attribute_group_name, None)
                if attribute_group is not None:
                    node_attributes.update(__ParseAttributeGroup(attribute_group,
                                                                 Attribute.Center.Node))
        for attribute in node_attributes.values():
            node_grid.append(attribute)

        # Add node IDs as an attribute
        node_id_attribute = Attribute("ID", Attribute.Center.Node)
        node_id_attribute.append(root_data.node_ids)
        node_attributes["ID"] = node_id_attribute
        node_grid.append(node_id_attribute)

        grid_tree.append(node_grid)

        # Add elements and conditions if the subgroup contains them
        for cell_type, cell_topologies, cell_index_maps, cell_ids, attribute_group_names in (("Elements",
                                                                                              root_data.element_topologies,
                                                                                              root_data.element_index_maps,
                                                                                              root_data.element_ids,
                                                                                              ("ElementDataValues", "ElementFlagValues")),
                                                                                              ("Conditions",
                                                                                              root_data.condition_topologies,
                                                                                              root_data.condition_index_maps,
                                                                                              root_data.condition_ids,
                                                                                              ("ConditionDataValues", "ConditionFlagValues"))):
            cell_groups: Optional[h5py.Group] = path.get(cell_type, None)
            if cell_groups is not None:
                for cell_name, cell_group in cell_groups.items():
                    # Add the mesh to the current grid level
                    cell_subgroup_name = f"{name}.{cell_name}" if subgroup_naming == SubgroupNaming.Paraview else cell_name
                    cell_grid = GridLeaf(cell_subgroup_name)
                    __TimeStamp(cell_grid, time)

                    cell_type_index_set = LeafDataItem(HDF5Data.FromDataset(cell_group["TypeIndices"]))
                    cell_topology_set: DataItem = cell_topologies[cell_name]
                    topology_type = __ParseCellType(cell_name, cell_topology_set.GetShape()[1])
                    cell_topology = Topology(topology_type)
                    maybe_cell_topology_data = MakeCoordinateSlice(
                        cell_type_index_set,
                        cell_topology_set,
                        list(range(cell_topology_set.GetShape()[-1])))

                    if maybe_cell_topology_data is None:
                        continue

                    cell_topology.append(maybe_cell_topology_data)
                    cell_grid.append(cell_topology)
                    cell_grid.append(node_geometry)

                    # Add node attributes to the current grid level
                    for attribute in node_attributes.values():
                        cell_grid.append(attribute)

                    # Add cell attributes to the current grid level
                    cell_index_set = CoordinateDataItem(cell_type_index_set, cell_index_maps[cell_name])
                    if attribute_path is not None:
                        for attribute_group_name in attribute_group_names:
                            attribute_group: Optional[h5py.Group] = attribute_path.get(attribute_group_name, None)
                            if attribute_group is not None:
                                for attribute in __ParseAttributeGroup(attribute_group,
                                                                       Attribute.Center.Cell,
                                                                       index_set = cell_index_set).values():
                                    cell_grid.append(attribute)

                    # Add cell IDs to the current grid level
                    cell_id_attribute = Attribute("ID", Attribute.Center.Cell)
                    cell_id_attribute.append(CoordinateDataItem(cell_index_set, cell_ids))
                    cell_grid.append(cell_id_attribute)

                    # Insert the current grid level into the grid tree
                    grid_tree.append(cell_grid)

    subgroups: Optional[h5py.Group] = path.get("SubModelParts", None)
    if subgroups is not None:
        for subgroup_name, subgroup in subgroups.items():
            if subgroup_naming == SubgroupNaming.Paraview:
                subgroup_name = f"{name}.{subgroup_name}"
            grid_tree.append(ParseMesh(subgroup,
                                       subgroup_name,
                                       attribute_path = attribute_path,
                                       time = time,
                                       root_data = root_data,
                                       subgroup_naming = subgroup_naming))

    return grid_tree



def ParseMesh(path: h5py.Group,
              name: str = "RootModelPart",
              attribute_path: Optional[h5py.Group] = None,
              time: Optional[Union[int,float]] = None,
              root_data: Optional[__RootData] = None,
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
    if root_data is None:
        return ParseRootMesh(path,
                             name = name,
                             attribute_path = attribute_path,
                             time = time,
                             subgroup_naming = subgroup_naming)
    else:
        return ParseSubmesh(path,
                            name,
                            root_data,
                            attribute_path = attribute_path,
                            time = time,
                            subgroup_naming = subgroup_naming)





