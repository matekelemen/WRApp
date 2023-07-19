""" @author Máté Kelemen"""

__all__ = [
    "GenerateXDMF",
    "GenerateXDMFOperation"
]

# --- External Imports ---
import h5py

# --- Core Imports ---
import KratosMultiphysics

# --- HDF5 Imports ---
import KratosMultiphysics.HDF5Application
from KratosMultiphysics.HDF5Application.xdmf_utils import RenumberConnectivitiesForXdmf,    \
                                                          CreateXdmfSpatialGrid,            \
                                                          XdmfResults,                      \
                                                          TemporalGrid,                     \
                                                          UniformGrid,                      \
                                                          SpatialGrid,                      \
                                                          Time,                             \
                                                          Domain,                           \
                                                          Xdmf

# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp

# --- STD Imports ---
import pathlib
import typing
import xml.etree.ElementTree
import multiprocessing
import os
import re
import json


def ExtractTimeLabel(placeholders: "dict[str,list[str]]", fallback: typing.Union[int,float]) -> typing.Union[int,float]:
    if "<step>" in placeholders:
        return int(placeholders["<step>"][0])
    elif "<time>" in placeholders:
        return float(placeholders["<time>"][0])
    return fallback



class _HDF5Path:
    """ @brief Filesystem path to an HDF5 file and a prefix within, uniquely identifying dataset/group.
        @classname _HDF5Path
    """

    def __init__(self,
                 file_path: pathlib.Path,
                 file_path_placeholder_map: "dict[str,list[str]]",
                 prefix: str,
                 prefix_placeholder_map: "dict[str,list[str]]"):
        self.__file_path = file_path
        self.__prefix = prefix

        # Try combing the two placeholder maps
        # if the two maps have identical keys, their values must match
        self.__placeholders = file_path_placeholder_map.copy()
        for key, value in prefix_placeholder_map.items():
            other = self.__placeholders.get(key, None)
            if other is not None: # both map have an entry for this key: check whether they're identical
                if other[0] != value[0]:
                    raise RuntimeError(f"Placeholder mismatch for key {key}: {other} != {value}")
            self.__placeholders[key] = value

        self.__label = ExtractTimeLabel(self.__placeholders, 0)


    @property
    def file_path(self) -> pathlib.Path:
        return self.__file_path


    @property
    def prefix(self) -> str:
        return self.__prefix


    @property
    def placeholders(self) -> "dict[str,list[str]]":
        return self.__placeholders


    @property
    def label(self) -> typing.Union[int,float]:
        return self.__label


    def __lt__(self, right: "_HDF5Path") -> bool:
        return self.label < right.label


    def __eq__(self, right: "_HDF5Path") -> bool:
        return self.label == right.label


    def __le__(self, right: "_HDF5Path") -> bool:
        return self.label < right.label or self.label == right.label



class _Dataset:
    """ @brief An @ref _HDF5Path with an associated mesh, also represented by an @ref _HDF5Path.
        @classname _Dataset
    """

    def __init__(self,
                 results: _HDF5Path,
                 mesh: _HDF5Path,
                 unique_mesh: bool):
        self.__results = results
        self.__mesh = mesh
        self.__unique_mesh = unique_mesh


    def HasUniqueMesh(self) -> bool:
        return self.__unique_mesh


    @property
    def results(self) -> _HDF5Path:
        return self.__results


    @property
    def mesh(self) -> _HDF5Path:
        return self.__mesh



class _Batch:
    """ @brief A set of HDF5 files and related data to process.
        @classname _Batch
    """

    def __init__(self,
                 datasets: "list[_Dataset]",
                 output_path: pathlib.Path):
        self.__datasets = datasets
        self.__output_path = output_path


    @property
    def datasets(self) -> "list[_Dataset]":
        return self.__datasets


    @property
    def output_path(self) -> pathlib.Path:
        return self.__output_path



def GlobHDF5(pattern: WRApp.ModelPartPattern,
             file: h5py.File) -> "list[str]":
    stack: "list[str]" = ["/"]
    regex_string = pattern.GetRegexString()
    if not pattern.GetPatternString().startswith("/"):
        raise RuntimeError(f"HDF5 prefixes must be absolute, and begin with '/'. '{pattern.GetPatternString()}' does not satisfy this condition.")

    for component in regex_string[1:-1].split("/")[1:]:
        if not stack:
            break
        regex = re.compile(component)
        local_stack = stack
        stack = []
        for path in local_stack:
            for item in file[path].keys():
                if regex.match(item):
                    stack.append(f"{path}{'/' if path != '/' else ''}{item}")

    return stack



def InputFileOrdering(item: "tuple[str,dict[str,list[str]],bool]") -> typing.Union[int,float,str]:
    """ @brief Takes a file name and its output from @ref ModelPartPattern, and extract data on which it should be ordered.
        @details Ordering happens on the first available variable in the following list:
                 - step index, if present in the match results
                 - time, if present in the match results
                 - 0
    """
    # item: {file_path, match_dict, has_mesh}
    return ExtractTimeLabel(item[1], 0)



def MakeJournal(input_file_pattern: str,
                results_prefix: str,
                mesh_prefix: str,
                output_path: str,
                verbose: bool = False) -> None:
    """ @brief Create a @ref Kratos::Journal from globbed paths."""
    # Collect all files and sort them in chronological order (analysis time/step)
    input_pattern = WRApp.ModelPartPattern(str(pathlib.Path(input_file_pattern).absolute()))
    results_pattern = WRApp.ModelPartPattern(results_prefix)
    mesh_pattern = WRApp.ModelPartPattern(mesh_prefix)

    with open(output_path, "w") as journal:
        for file_path, file_placeholders in sorted(((path, input_pattern.Match(str(path))) for path in input_pattern.Glob()), key = InputFileOrdering):
            with h5py.File(file_path, "r") as file:
                results = sorted(
                    _HDF5Path(file_path,
                              file_placeholders,
                              prefix,
                              results_pattern.Match(prefix))
                    for prefix in GlobHDF5(results_pattern, file))
                meshes = sorted(
                    _HDF5Path(file_path,
                              file_placeholders,
                              prefix,
                              mesh_pattern.Match(prefix))
                    for prefix in GlobHDF5(mesh_pattern, file))
            while results:
                current_results = results.pop(0)

                # Check whether there's a mesh corresponding to the current results
                current_mesh: typing.Optional[_HDF5Path] = None
                while meshes and meshes[0] <= current_results:
                    current_mesh = meshes.pop(0)

                entry = {
                    "results" : {
                        "file_name" : str(current_results.file_path),
                        "prefix" : str(current_results.prefix)
                    }
                }

                if current_mesh is not None:
                    entry["mesh"] = {
                        "file_name" : str(current_mesh.file_path),
                        "prefix" : str(current_mesh.prefix)
                    }

                journal.write(json.dumps(entry))
                journal.write("\n")



def MakeBatches(journal_path: pathlib.Path,
                output_path: str,
                batch_size: int = -1,
                verbose: bool = False) -> typing.Generator[_Batch,None,None]:
    if batch_size == 0:
        raise ValueError(f"Invalid batch size: {batch_size}")

    with open(journal_path, "r") as journal:
        datasets: "list[_Dataset]" = []
        current_mesh: typing.Optional[_HDF5Path] = None
        output_pattern = WRApp.PlaceholderPattern(output_path,
                                                  {"<batch>" : WRApp.PlaceholderPattern.UnsignedInteger})
        i_batch = 0
        for entry in journal.readlines():
            map = json.loads(entry)

            # Get the mesh from the entry if it has one
            mesh = map.get("mesh", None)
            if mesh is not None:
                current_mesh = _HDF5Path(pathlib.Path(mesh["file_name"]),
                                         {},
                                         mesh["prefix"],
                                         {})

            # Get results
            current_results = _HDF5Path(pathlib.Path(map["results"]["file_name"]),
                                        {},
                                        map["results"]["prefix"],
                                        {})

            if current_mesh is None:
                raise RuntimeError(f"Results in file '{current_results.file_path}' at '{current_results.prefix}' have no corresponding mesh")

            datasets.append(_Dataset(current_results,
                                     current_mesh,
                                     mesh is not None))

            if len(datasets) == batch_size:
                yield _Batch(datasets, output_pattern.Apply({"<batch>" : str(i_batch)}))
                datasets = []
                i_batch += 1

    if datasets:
        yield _Batch(datasets, output_pattern.Apply({"<batch>" : str(i_batch)}))
    return



def CreateXdmfTemporalGridFromMultifile(batch: _Batch, verbose: bool = False) -> TemporalGrid:
    temporal_grid = TemporalGrid()
    spatial_grid = SpatialGrid()
    for i_dataset, dataset in enumerate(batch.datasets):
        current_spatial_grid = SpatialGrid()
        if dataset.HasUniqueMesh() or i_dataset == 0:
            with h5py.File(dataset.mesh.file_path, "r") as file:
                spatial_grid = CreateXdmfSpatialGrid(file[dataset.mesh.prefix])
        for grid in spatial_grid.grids:
            current_spatial_grid.add_grid(UniformGrid(grid.name,
                                                      grid.geometry,
                                                      grid.topology))
        with h5py.File(dataset.results.file_path, "r") as file:
            for result in XdmfResults(file[dataset.results.prefix]):
                current_spatial_grid.add_attribute(result)
            temporal_grid.add_grid(Time(i_dataset), current_spatial_grid)

        if verbose:
            pass # todo
    return temporal_grid



def BatchGenerateXDMF(arguments: "tuple[_Batch,bool]") -> None:
    """ @brief Generate an XDMF file from a batch of input files.
        @details The arguments are packaged into a single tuple:
                 - batch: Batch (batch to process)
                 - mesh_prefix: str (prefix of the mesh in HDF5 files that contain mesh data)
                 - results_prefix: str (prefix of the mesh in HDF5 files that contain results data)
                 - verbose: bool (print status messages while processing)
    """
    temporal_grid = CreateXdmfTemporalGridFromMultifile(*arguments)
    domain = Domain(temporal_grid)
    xdmf = Xdmf(domain)
    xml.etree.ElementTree.ElementTree(xdmf.create_xml_element()).write(arguments[0].output_path)



def GenerateXDMF(journal_path: pathlib.Path,
                 output_pattern: str = "batch_<batch>.xdmf",
                 batch_size: int = -1,
                 verbose: bool = False) -> None:
    """ @brief Generate XDMF output for an existing set of HDF5 output files."""
    batches = MakeBatches(journal_path,
                          output_pattern,
                          batch_size,
                          verbose = verbose)

    thread_count = int(os.environ.get("OMP_NUM_THREADS", max([multiprocessing.cpu_count() - 1,1])))
    if 1 < thread_count:
        with multiprocessing.Pool(thread_count) as pool:
            pool.map(BatchGenerateXDMF, ((batch, verbose) for batch in batches))
    else:
        for batch in batches:
            BatchGenerateXDMF((batch, verbose))


class GenerateXDMFOperation(KratosMultiphysics.Operation, WRApp.WRAppClass):
    """ @brief Wrap @ref GenerateXDMF in a kratos @ref Operation.
        @classname GenerateXDMFOperation
        @details Default parameters:
                 @code
                 {
                    "file_pattern": "",                         // <== input file pattern compatible with ModelPartPattern
                    "mesh_prefix" : "/ModelData",               // <== prefix of the mesh within HDF5 files
                    "results_prefix" : "/ResultsData",          // <== prefix of the results within HDF5 files
                    "batch_size" : -1,                          // <== number of input files to process per output xdmf
                    "output_pattern" : "batch_<batch>.xdmf",    // <== output file name pattern; may contain the "<batch>" placeholder
                    "verbose" : false                           // <== print status messages
                 }
                 @endcode
    """

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        KratosMultiphysics.Operation.__init__(self)
        WRApp.WRAppClass.__init__(self)
        self.__parameters = parameters
        self.__parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())
        self.__batch_size = parameters["batch_size"].GetInt()
        self.__output_pattern = parameters["output_pattern"].GetString()


    def Execute(self) -> None:
        GenerateXDMF(pathlib.Path(self.__parameters["journal_path"].GetString()),
                     output_pattern = self.__output_pattern,
                     batch_size = self.__batch_size,
                     verbose = self.__parameters["verbose"].GetBool())


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters("""{
            "journal_path" : "",
            "batch_size" : -1,
            "output_pattern" : "batch_<batch>.xdmf",
            "verbose" : false
        }""")



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser("generate-xdmf")

    parser.add_argument("journal_path",
                        type = pathlib.Path,
                        help = "Journal file to find the results from.")
    parser.add_argument("-o",
                        "--output-pattern",
                        dest = "output_pattern",
                        type = str,
                        default = "batch_<batch>.xdmf",
                        help = "Path to write the output XDMF to. Warning: existing files will be overwritten.")
    parser.add_argument("-b",
                        "--batch-size",
                        dest = "batch_size",
                        type = int,
                        default = -1,
                        help = "Max number of input files to process per output xdmf.")
    parser.add_argument("-v",
                        "--verbose",
                        dest = "verbose",
                        action = "store_const",
                        default = False,
                        const = True,
                        help = "Print status messages while processing.")

    arguments = parser.parse_args()
    GenerateXDMF(arguments.journal_path,
                 output_pattern = arguments.output_pattern,
                 batch_size = arguments.batch_size,
                 verbose = arguments.verbose)
