# --- Core Imports ---
import KratosMultiphysics

# --- HDF5 Imports ---
import KratosMultiphysics.HDF5Application as KratosHDF5
from KratosMultiphysics.HDF5Application.core.xdmf import SpatialGrid,           \
                                                         HDF5UniformDataItem,   \
                                                         Geometry,              \
                                                         TopologyCellType,      \
                                                         UniformMeshTopology,   \
                                                         UniformGrid,           \
                                                         NodalData,             \
                                                         ElementData,           \
                                                         ConditionData,         \
                                                         TemporalGrid,          \
                                                         Time,                  \
                                                         Domain,                \
                                                         Xdmf,                  \
                                                         DataItem

# --- STD Imports ---
import xml.etree.ElementTree as ET
import os
from itertools import chain
from contextlib import contextmanager
import re
from typing import Union


try:
    import h5py
except ModuleNotFoundError:
    warn_msg = "h5py module was not found!"
    KratosMultiphysics.Logger.PrintWarning(__name__, warn_msg)
else:


    class HDF5CoordinateDataItem(DataItem):

        def __init__(self,
                     index_set: h5py.Dataset,
                     reference_set: h5py.Dataset):
            self.__index_set = HDF5UniformDataItem(index_set)
            self.__reference_set = HDF5UniformDataItem(reference_set)

        @property
        def dimensions(self) -> "list[int]":
            return self.__index_set.dimensions + self.__reference_set.dimensions[1:]

        @property
        def attrib(self) -> "dict[str,str]":
            output = {"ItemType" : "coordinates",
                      "Type"     : "Coordinate"}
            reference_attributes = self.__reference_set.attrib
            for attribute_name in ("DataType", "Precision"):
                if attribute_name in reference_attributes:
                    output[attribute_name] = reference_attributes[attribute_name]
            return output

        def create_xml_element(self) -> ET.Element:
            output = ET.Element(self.xml_tag, self.attrib)
            index_element: ET.Element = self.__index_set.create_xml_element()
            reference_element: ET.Element = self.__reference_set.create_xml_element()

            # The "DataType" attribute of the index set should be "Int", but apparently
            # specifying it explicitly is prohibited, so it must be stripped out.
            for attribute_name in ("DataType", "Precision"):
                if attribute_name in index_element.attrib:
                    del index_element.attrib[attribute_name]

            # The root DataItem may have a name, but paraview craps out if the index set
            # or the reference set has a name as well ...
            for element in (index_element, reference_element):
                if "Name" in element.attrib:
                    del element.attrib["Name"]

            output.append(index_element)
            output.append(reference_element)
            return output


    @contextmanager
    def TryOpenH5File(name, mode=None, driver=None, **kwds):
        """A context manager wrapper for the opened file.

        In case the file cannot be opened, yield None rather than raise an
        exception.  This can be the case if the file is already opened.
        """
        try:
            with h5py.File(name, mode, driver=driver, **kwds) as f:
                yield f
        except OSError:
            warn_msg = 'No xdmf-data was written for file:\n"' + name + '"'
            KratosMultiphysics.Logger.PrintWarning("XDMF", warn_msg)
            yield None


    def RenumberConnectivitiesForXdmf(filename_or_list_of_filenames, h5path_to_mesh):
        """Renumber mesh connectivities for XDMF.

        Keyword arguments:
        filename_or_list_of_filenames -- the HDF5 file(s) to renumber
        h5path_to_mesh -- the internal HDF5 file path to the mesh

        The mesh connectivities must be renumbered for XDMF by the node's array
        index rather than its ID.  The renumbered connectivities are stored in
        HDF5 and referenced by the XDMF Grid.  If a file cannot be opened, it is
        skipped.

        See:
        - XdmfConnectivitiesWriterProcess.
        """
        for path in list(filename_or_list_of_filenames):
            skip = True
            with TryOpenH5File(path, "r") as f:
                if not f:
                    continue
                if h5path_to_mesh in f:
                    skip = "Xdmf" in f[h5path_to_mesh]
            if not skip:
                KratosHDF5.HDF5XdmfConnectivitiesWriterProcess(
                    path, h5path_to_mesh).Execute()


    def GetListOfSpatialGrids(spatial_grids_list: "list[list[str]]",
                              h5_model_part: h5py.Group,
                              current_path: str) -> None:
        if (isinstance(h5_model_part, h5py.Dataset)):
            # add point clouds
            spatial_grids_list.append([str(h5_model_part.name), current_path])
        else:
            for key in h5_model_part.keys():
                if (key == "Conditions" or key == "Elements"):
                    spatial_grids_list.append([str(h5_model_part.name) + "/" + str(key), current_path + "." + str(key)])
                elif isinstance(h5_model_part[key], h5py.Group):
                    GetListOfSpatialGrids(spatial_grids_list, h5_model_part[key], current_path + "." + str(key))


    def CreateXdmfSpatialGrid(h5_model_part):
        """Return an XDMF Grid object corresponding to a mesh in an HDF5 file.

        Keyword arguments:
        h5_model_part -- the HDF5 group containing the model part

        Expects:
        - element connectivities in h5_model_part["Xdmf/Elements/<element-name>"].
        Each connectivities has attributes "Dimension" and "NumberOfNodes".  For
        example, "Element2D3N" has "Dimension" 2 and "NumberOfNodes" 3.  The
        connectivities differ from the normal mdpa connectivities in that they
        directly index the array of nodal coordinates.  Currently there is
        no other way to post-process the mesh with Xdmf.

        See:
        - core.operations.ModelPartOutput,
        - core.operations.PartitionedModelPartOutput,
        - RenumberConnectivitiesForXdmf.
        """
        sgrid = SpatialGrid()
        geom = Geometry(HDF5UniformDataItem(
            h5_model_part["Nodes/Local/Coordinates"]))

        spatial_grids_list = []
        GetListOfSpatialGrids(spatial_grids_list, h5_model_part["Xdmf"], "RootModelPart")

        for spatial_grid in spatial_grids_list:
            spatial_grid_location = spatial_grid[0]
            spatial_grid_name = spatial_grid[1]
            current_h5_item = h5_model_part[spatial_grid_location]
            if (isinstance(current_h5_item, h5py.Dataset)):
                cell_type = TopologyCellType(3, 1)
                points = HDF5UniformDataItem(current_h5_item)
                topology = UniformMeshTopology(cell_type, points)
                sgrid.add_grid(UniformGrid(spatial_grid_name + "." + name, geom, topology))
            else:
                for name, value in current_h5_item.items():
                    cell_type = TopologyCellType(
                        value.attrs["WorkingSpaceDimension"], value.attrs["NumberOfNodes"])
                    connectivities = HDF5UniformDataItem(value["Connectivities"])
                    topology = UniformMeshTopology(cell_type, connectivities)
                    sgrid.add_grid(UniformGrid(spatial_grid_name + "." + name, geom, topology))

        return sgrid


    def Has_dtype(item): return hasattr(item[1], 'dtype')


    def XdmfNodalResults(h5_results):
        """Return a list of XDMF Attribute objects for nodal results in an HDF5 file.

        Keyword arguments:
        h5_results -- the HDF5 group containing the results

        Checks for results stored in data sets by variable name in:
        - h5_results["NodalSolutionStepData/<variable-name>"]
        - h5_results["NodalDataValues/<variable-name>"]

        Expects:
        - each result variable occurs only once

        If no results are found, returns an empty list.

        See:
        - core.operations.NodalSolutionStepDataOutput,
        - core.operations.NodalDataValueOutput.
        """
        results = {}
        for path in ["NodalSolutionStepData", "NodalDataValues"]:
            try:
                grp = h5_results[path]
            except KeyError:
                continue
            for variable, data in filter(Has_dtype, grp.items()):
                if variable in results:
                    # A variable can exist in the nodal solution step data or
                    # non-historical nodal data value container, but not both.
                    raise RuntimeError('Nodal result variable "' +
                                    variable + '" already exists.')
                results[variable] = NodalData(variable, HDF5UniformDataItem(data))
        return list(results.values())


    def XdmfNodalFlags(h5_results):
        """Return a list of XDMF Attribute objects for nodal flags in an HDF5 file.

        Keyword arguments:
        h5_results -- the HDF5 group containing the flags

        Checks for flags stored in data sets by variable name in:
        - h5_flags["NodalFlagValues/<flag-name>"]

        Expects:
        - each flag variable occurs only once

        If no flags are found, returns an empty list.

        See:
        - core.operations.NodalFlagsValueOutput.
        """

        results_path = "NodalFlagValues"
        results = []
        try:
            grp = h5_results[results_path]
        except KeyError:
            return results
        for variable, data in filter(Has_dtype, grp.items()):
            r = NodalData(variable, HDF5UniformDataItem(data))
            results.append(r)
        return results


    def XdmfElementResults(h5_results):
        """Return a list of XDMF Attribute objects for element results in an HDF5 file.

        Keyword arguments:
        h5_results -- the HDF5 group containing the results

        Checks for results stored by variable name in:
        - h5_results["ElementDataValues/<variable>"]

        If no results are found, returns an empty list.

        See:
        - core.operations.ElementDataValueOutput.
        """
        results_path = "ElementDataValues"
        results = []
        try:
            grp = h5_results[results_path]
        except KeyError:
            return results
        for variable, data in filter(Has_dtype, grp.items()):
            r = ElementData(variable, HDF5UniformDataItem(data))
            results.append(r)
        return results

    def XdmfElementFlags(h5_results):
        """Return a list of XDMF Attribute objects for element flags in an HDF5 file.

        Keyword arguments:
        h5_flags -- the HDF5 group containing the flags

        Checks for flags stored by variable name in:
        - h5_flags["ElementFlagValues/<flag-name>"]

        If no flags are found, returns an empty list.

        See:
        - core.operations.ElementFlagValueOutput.
        """
        results_path = "ElementFlagValues"
        results = []
        try:
            grp = h5_results[results_path]
        except KeyError:
            return results
        for variable, data in filter(Has_dtype, grp.items()):
            r = ElementData(variable, HDF5UniformDataItem(data))
            results.append(r)
        return results

    def XdmfElementGaussPointValues(h5_results):
        """Return a list of XDMF Attribute objects for element integration point values in an HDF5 file.

        Keyword arguments:
        h5_results -- the HDF5 group containing the results

        Checks for results stored by variable name in:
        - h5_results["ElementGaussPointValues/<variable>"]

        If no results are found, returns an empty list.

        See:
        - core.operations.ElementGaussPointOutput.
        """
        results_path = "ElementGaussPointValues"
        results = []
        try:
            grp = h5_results[results_path]
        except KeyError:
            return results
        for variable, data in filter(Has_dtype, grp.items()):
            r = ElementData(variable, HDF5UniformDataItem(data))
            results.append(r)
        return results

    def XdmfConditionResults(h5_results):
        """Return a list of XDMF Attribute objects for element results in an HDF5 file.

        Keyword arguments:
        h5_results -- the HDF5 group containing the results

        Checks for results stored by variable name in:
        - h5_results["ConditionDataValues/<variable>"]

        If no results are found, returns an empty list.

        See:
        - core.operations.ConditionDataValueOutput.
        """
        results_path = "ConditionDataValues"
        results = []
        try:
            grp = h5_results[results_path]
        except KeyError:
            return results
        for variable, data in filter(Has_dtype, grp.items()):
            r = ConditionData(variable, HDF5UniformDataItem(data))
            results.append(r)
        return results

    def XdmfConditionFlags(h5_results):
        """Return a list of XDMF Attribute objects for element flags in an HDF5 file.

        Keyword arguments:
        h5_flags -- the HDF5 group containing the flags

        Checks for flags stored by variable name in:
        - h5_flags["ConditionFlagValues/<flag-name>"]

        If no flags are found, returns an empty list.

        See:
        - core.operations.ConditionFlagValueOutput.
        """
        results_path = "ConditionFlagValues"
        results = []
        try:
            grp = h5_results[results_path]
        except KeyError:
            return results
        for variable, data in filter(Has_dtype, grp.items()):
            r = ConditionData(variable, HDF5UniformDataItem(data))
            results.append(r)
        return results

    def XdmfConditionGaussPointValues(h5_results):
        """Return a list of XDMF Attribute objects for element integration point values in an HDF5 file.

        Keyword arguments:
        h5_results -- the HDF5 group containing the results

        Checks for results stored by variable name in:
        - h5_results["ConditionGaussPointValues/<variable>"]

        If no results are found, returns an empty list.

        See:
        - core.operations.ConditionGaussPointOutput.
        """
        results_path = "ConditionGaussPointValues"
        results = []
        try:
            grp = h5_results[results_path]
        except KeyError:
            return results
        for variable, data in filter(Has_dtype, grp.items()):
            r = ElementData(variable, HDF5UniformDataItem(data))
            results.append(r)
        return results


    def XdmfResults(h5_results: h5py.Group):
        """Return a list of XDMF Attribute objects for results in an HDF5 file.

        Keyword arguments:
        h5_results -- the HDF5 group containing the results
        """
        return list(
            chain(
                XdmfNodalResults(h5_results),
                XdmfNodalFlags(h5_results),
                XdmfElementResults(h5_results),
                XdmfElementFlags(h5_results),
                XdmfElementGaussPointValues(h5_results),
                XdmfConditionResults(h5_results),
                XdmfConditionFlags(h5_results),
                XdmfConditionGaussPointValues(h5_results)
            )
        )


    def TimeLabel(file_path):
        """Return the time string from the file name.

        E.g.:
        'kratos-123.h5' -> '123'
        'kratos-1.2.h5' -> '1.2'
        'kratos-1.2e+00.h5' -> '1.2e+00'

        Returns empty string if not found.
        """
        # Is there a better way to do this?
        temp_file_path = file_path.replace("E-", "E*")
        temp_file_path = temp_file_path.replace("e-", "e*")

        dash_split = temp_file_path[:temp_file_path.rfind(".")].split("-")
        dash_split[-1] = dash_split[-1].replace("E*", "E-")
        dash_split[-1] = dash_split[-1].replace("e*", "e-")

        float_regex = re.compile(r'^[-+]?([0-9]+|[0-9]*\.[0-9]+)([eE][-+]?[0-9]+)?$')
        if (float_regex.match(dash_split[-1])):
            return dash_split[-1]
        else:
            return ""


    def TimeFromFileName(file_path):
        """Return the time value for the file name.

        If the file name contains no time value, zero time value is assumed.

        """
        label = TimeLabel(file_path)
        if label == "":
            return 0.0
        else:
            return float(label)


    def FindMatchingFiles(pattern):
        """Return a list of HDF5 files matching the given file name pattern.

        For example, "./sim/kratos" matches:
        - ./sim/kratos.h5
        - ./sim/kratos-0.0000.h5
        - ./sim/kratos-0.2000.h5
        - etc.
        """
        path, _ = os.path.split(pattern)
        if path == "":
            path = "."  # os.listdir fails with empty path
        def match(s): return s.startswith(pattern) and s.endswith(".h5")
        return list(filter(match, os.listdir(path)))


    def GetSortedListOfFiles(pattern):
        """Return sorted file list based on the time stamp

        see @FindMatchingFiles
        """
        list_of_files = FindMatchingFiles(pattern)
        list_of_files.sort(key=TimeFromFileName)
        return list_of_files

    def GetStep(value, patterns):
        if len(patterns) == 1:
            return 0
        else:
            if (len(patterns[1]) == 0):
                return int(value[len(patterns[0]):])
            else:
                return int(value[len(patterns[0]):-len(patterns[1])])

    def GetMatchingGroupNames(output_dict, value, patterns, pattern_with_wildcards):
        matching_value = re.search(pattern_with_wildcards, value)
        if  matching_value is not None:
            current_group = str(matching_value.group())
            output_dict[GetStep(current_group, patterns)] = "/" + current_group


    def WriteMultifileTemporalAnalysisToXdmf(ospath, h5path_to_mesh, h5path_to_results):
        """Write XDMF metadata for a temporal analysis from multiple HDF5 files.

        Keyword arguments:
        ospath -- path to one of the HDF5 files or the corresponding XDMF output file.
        h5path_to_mesh -- the internal HDF5 file path to the mesh
        h5path_to_results -- the internal HDF5 file path to the results
        """
        pat = ospath
        # Strip any time label from the file name.
        time_label = TimeLabel(pat)
        pat = pat.rstrip('.h5').rstrip('.xdmf')
        if time_label:
            pat = pat.rstrip(time_label).rstrip("-")
        # Generate the temporal grid.
        list_of_files = GetSortedListOfFiles(pat)
        RenumberConnectivitiesForXdmf(list_of_files, h5path_to_mesh)
        temporal_grid = CreateXdmfTemporalGridFromMultifile(
            list_of_files, h5path_to_mesh, h5path_to_results)
        domain = Domain(temporal_grid)
        xdmf = Xdmf(domain)
        # Write the XML tree containing the XDMF metadata to the file.
        ET.ElementTree(xdmf.create_xml_element()).write(pat + ".xdmf")


    def CreateXdmfTemporalGridFromSinglefile(h5_file_name,
                                            h5path_pattern_to_mesh,
                                            h5path_pattern_to_results,
                                            require_results: bool = False):
        """Return an XDMF Grid object for a list of temporal results in a single HDF5 file.

        Keyword arguments:
        h5_file_name -- the HDF5 file to be parsed
        h5path_pattern_to_mesh -- the internal HDF5 file path pattern to the mesh [ only <step> flag is supported ]
        h5path_pattern_to_results -- the internal HDF5 file path pattern to the results [ only <step> flag is supported ]

        Expects:
        - In prefixes, <step> flag is used maximum of one time only
        - If single mesh description is found, it is considered as single mesh temporal output
        """
        tgrid = TemporalGrid()

        h5path_pattern_to_mesh_wild_cards = h5path_pattern_to_mesh.replace("<step>", "\d*")
        h5path_patterns_to_mesh = h5path_pattern_to_mesh.split("<step>")
        if (len(h5path_patterns_to_mesh) > 2):
            raise RuntimeError("'<step>' flag can only be used once in a prefix")

        h5path_pattern_to_results_wild_cards = h5path_pattern_to_results.replace("<step>", "\d*")
        h5path_patterns_to_results = h5path_pattern_to_results.split("<step>")
        if (len(h5path_patterns_to_results) > 2):
            raise RuntimeError("'<step>' flag can only be used once in a prefix")

        renumbering_mesh_paths = []
        with TryOpenH5File(h5_file_name, "r") as file_:
            if not file_:
                raise RuntimeError("Unsupported h5 file provided [ file_name = {:s} ].".format(h5_file_name))

            output_meshes_dict = {}
            file_.visit(lambda x : GetMatchingGroupNames(output_meshes_dict, x, h5path_patterns_to_mesh, h5path_pattern_to_mesh_wild_cards))

            for _, v in output_meshes_dict.items():
                if "Xdmf" not in file_[v]:
                    renumbering_mesh_paths.append(v)

            if len(output_meshes_dict.keys()) == 0:
                raise RuntimeError("No grid information is found in the given hdf5 file matching the given pattern [ file_name = {:s}, pattern = {:s} ].".format(h5_file_name, h5path_pattern_to_mesh))

        # renumber xdmf connectivities
        for v in renumbering_mesh_paths:
            KratosHDF5.HDF5XdmfConnectivitiesWriterProcess(
                h5_file_name, v).Execute()

        with TryOpenH5File(h5_file_name, "r") as file_:
            output_results_dict = {}
            file_.visit(lambda x : GetMatchingGroupNames(output_results_dict, x, h5path_patterns_to_results, h5path_pattern_to_results_wild_cards))

            if not output_results_dict:
                raise RuntimeError("No results data is found in the given hdf5 file matching the given pattern [ file_name = {:s}, pattern = {:s} ].".format(h5_file_name, h5path_pattern_to_results))

            compound_dict = {}
            for key in output_meshes_dict:
                compound_dict[key] = (True, False)
            for key in output_results_dict:
                if key in compound_dict:
                    compound_dict[key][1] = True
                else:
                    compound_dict[key] = (False, True)

            sgrid = None
            for key, (has_mesh, has_results) in compound_dict.items():
                current_sgrid = SpatialGrid()
                if has_mesh:
                    sgrid = CreateXdmfSpatialGrid(file_[output_meshes_dict[key]])
                    for g in sgrid.grids:
                        current_sgrid.add_grid(UniformGrid(g.name, g.geometry, g.topology))

                if has_results:
                    if sgrid is None:
                        raise RuntimeError(f"No mesh found for results at {key}")
                    for g in sgrid.grids:
                        current_sgrid.add_grid(UniformGrid(g.name, g.geometry, g.topology))
                    for result in XdmfResults(file_[output_results_dict[key]]):
                        current_sgrid.add_attribute(result)

                if has_results or not (require_results and not has_results):
                    tgrid.add_grid(Time(key), current_sgrid)

        return tgrid


    def WriteSinglefileTemporalAnalysisToXdmf(h5_file_name,
                                            h5path_pattern_to_mesh,
                                            h5path_pattern_to_results,
                                            require_results: bool = False):
        """Write XDMF metadata for a temporal analysis from single HDF5 file.

        Keyword arguments:
        h5_file_name -- hdf5 filename
        h5path_pattern_to_mesh -- the internal HDF5 file path pattern to the mesh [ only <step> flag is supported ]
        h5path_to_results -- the internal HDF5 file path pattern to the results [ only <step> flag is supported ]
        """

        if (h5path_pattern_to_mesh.startswith("/")):
            h5path_pattern_to_mesh = h5path_pattern_to_mesh[1:]

        if (h5path_pattern_to_results.startswith("/")):
            h5path_pattern_to_results = h5path_pattern_to_results[1:]

        temporal_grid = CreateXdmfTemporalGridFromSinglefile(h5_file_name,
                                                            h5path_pattern_to_mesh,
                                                            h5path_pattern_to_results,
                                                            require_results = require_results)
        domain = Domain(temporal_grid)
        xdmf = Xdmf(domain)
        # Write the XML tree containing the XDMF metadata to the file.
        ET.ElementTree(xdmf.create_xml_element()).write(h5_file_name[:h5_file_name.rfind(".")] + ".xdmf")
