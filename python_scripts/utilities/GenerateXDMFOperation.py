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


class Batch:
    """ @brief A set of HDF5 files and related data to process."""

    def __init__(self,
                 files: "list[tuple[pathlib.Path,typing.Optional[pathlib.Path],dict[str,list[str]]]]",
                 mesh_prefix: str,
                 results_prefix: str,
                 output_file: pathlib.Path):
        self.files = files
        self.mesh_prefix = mesh_prefix
        self.results_prefix = results_prefix
        self.output_file = output_file


def ExtractTimeLabel(placeholders: "dict[str,list[str]]", fallback: str) -> typing.Union[int,float,str]:
    if "<step>" in placeholders:
        return int(placeholders["<step>"][0])
    elif "<time>" in placeholders:
        return float(placeholders["<time>"][0])
    return fallback


def InputFileOrdering(item: "tuple[str,dict[str,list[str]],bool]") -> typing.Union[int,float,str]:
    """ @brief Takes a file name and its output from @ref ModelPartPattern, and extract data on which it should be ordered.
        @details Ordering happens on the first available variable in the following list:
                 - step index, if present in the match results
                 - time, if present in the match results
                 - lexicographical ordering based on the file name, as fallback
    """
    # item: {file_path, match_dict, has_mesh}
    return ExtractTimeLabel(item[1], item[0])


def CreateXdmfTemporalGridFromMultifile(batch: Batch,
                                        mesh_prefix: str,
                                        results_prefix: str,
                                        verbose: bool = False) -> TemporalGrid:
    temporal_grid = TemporalGrid()
    spatial_grid = SpatialGrid()
    for i_file, (results_path, mesh_path, placeholder_map) in enumerate(batch.files):
        current_spatial_grid = SpatialGrid()
        if mesh_path is not None:
            with h5py.File(mesh_path, "r") as file:
                spatial_grid = CreateXdmfSpatialGrid(file[mesh_prefix])
        for grid in spatial_grid.grids:
            current_spatial_grid.add_grid(UniformGrid(grid.name,
                                                        grid.geometry,
                                                        grid.topology))
        with h5py.File(results_path, "r") as file:
            for result in XdmfResults(file[results_prefix]):
                current_spatial_grid.add_attribute(result)
            temporal_grid.add_grid(Time(ExtractTimeLabel(placeholder_map, "0")), current_spatial_grid)

        if verbose:
            pass # todo
    return temporal_grid


def HasMesh(path: pathlib.Path, mesh_prefix: str) -> bool:
    with h5py.File(path, "r") as file:
        return mesh_prefix in file


def MakeBatches(input_file_pattern: str,
                mesh_prefix: str,
                results_prefix: str,
                output_file_pattern: str,
                batch_size: int,
                verbose: bool = False) -> typing.Generator[Batch,None,None]:
    # Collect all files and sort them in chronological order (analysis time/step)
    input_pattern = WRApp.ModelPartPattern(str(pathlib.Path(input_file_pattern).absolute()))
    all_files = sorted([(str(path.absolute()),
                         input_pattern.Match(str(path)),
                         HasMesh(path, mesh_prefix)) for path in input_pattern.Glob()],
                       key = InputFileOrdering)

    # Spetial case: batch_size == -1 refers to creaing a single batch
    if batch_size == -1:
        batch_size = len(all_files)

    if verbose:
        KratosMultiphysics.Logger.PrintInfo("[XDMF]", f"Found {len(all_files)} matching '{input_file_pattern}'")

    output_pattern = WRApp.PlaceholderPattern(
        output_file_pattern,
        {"<batch>" : WRApp.PlaceholderPattern.UnsignedInteger})

    # Partition files into batches while making sure each batch has a mesh
    mesh_file: typing.Optional[pathlib.Path] = None
    files: "list[tuple[pathlib.Path,typing.Optional[pathlib.Path],dict[str,list[str]]]]" = [] # <== {results_file, mesh_file, placeholder_map}
    i_batch = 0
    for i_entry, (file_path, placeholders, has_mesh) in enumerate(all_files):
        if has_mesh:
            RenumberConnectivitiesForXdmf([file_path], mesh_prefix)

        if not (i_entry % batch_size) and i_entry:
            if verbose:
                KratosMultiphysics.Logger.PrintInfo("[XDMF]", f"Creating a batch from range '{files[0][0]}' - '{files[-1][0]}'")
            yield Batch(
                    files,
                    mesh_prefix,
                    results_prefix,
                    pathlib.Path(output_pattern.Apply({"<batch>" : str(i_batch)})))
            i_batch += 1
            files = []

        mesh_file = pathlib.Path(file_path) if has_mesh else mesh_file # <== update mesh file to the latest one
        if not files: # <== each batch needs a guaranteed (most recent) mesh file
            if mesh_file is None:
                raise RuntimeError(f"Missing mesh data for {all_files[0][0]}")
            files.append((pathlib.Path(file_path), mesh_file, placeholders))
        else:
            files.append((pathlib.Path(file_path),
                          mesh_file if has_mesh else None,
                          placeholders))

    # Last batch
    if files:
        if verbose:
                KratosMultiphysics.Logger.PrintInfo("[XDMF]", f"Creating a batch from range '{files[0][0]}' - '{files[-1][0]}'")
        yield Batch(
                files,
                mesh_prefix,
                results_prefix,
                pathlib.Path(output_pattern.Apply({"<batch>" : str(i_batch)})))

    return


def BatchGenerateXDMF(arguments: "tuple[Batch,str,str,bool]") -> None:
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
    xml.etree.ElementTree.ElementTree(xdmf.create_xml_element()).write(arguments[0].output_file)


def GenerateXDMF(file_pattern: str,
                 mesh_prefix: str = "/ModelData",
                 results_prefix: str = "/ResultsData",
                 output_pattern: str = "batch_<batch>.xdmf",
                 batch_size: int = -1,
                 verbose: bool = False) -> None:
    """ @brief Generate XDMF output for an existing set of HDF5 output files."""
    batches = MakeBatches(file_pattern,
                          mesh_prefix,
                          results_prefix,
                          output_pattern,
                          batch_size,
                          verbose = verbose)

    with multiprocessing.Pool() as pool:
        pool.map(BatchGenerateXDMF, ((batch, mesh_prefix, results_prefix, verbose) for batch in batches))


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
        GenerateXDMF(self.__parameters["file_pattern"].GetString(),
                     mesh_prefix = self.__parameters["mesh_prefix"].GetString(),
                     results_prefix = self.__parameters["results_prefix"].GetString(),
                     output_pattern = self.__output_pattern,
                     batch_size = self.__batch_size)


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters("""{
            "file_pattern": "",
            "mesh_prefix" : "/ModelData",
            "results_prefix" : "/ResultsData",
            "batch_size" : -1,
            "output_pattern" : "batch_<batch>.xdmf",
            "verbose" : false
        }""")



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser("generate-xdmf")

    parser.add_argument("file_pattern",
                        type = str,
                        help = "File path pattern to scan, compatible with ModelPartPattern.")
    parser.add_argument("-o",
                        "--output-pattern",
                        dest = "output_pattern",
                        type = str,
                        default = "batch_<batch>.xdmf",
                        help = "Path to write the output XDMF to. Warning: existing files will be overwritten.")
    parser.add_argument("-m",
                        "--mesh-prefix",
                        dest = "mesh_prefix",
                        type = str,
                        default = "/ModelData",
                        help = "Path within HDF5 files to mesh data. At least one HDF5 file must contain mesh data.")
    parser.add_argument("-r",
                        "--results-prefix",
                        dest = "results_prefix",
                        type = str,
                        default = "/ResultsData",
                        help = "Path within HDF5 files to results. All HDF5 files must contain this path.")
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
    GenerateXDMF(arguments.file_pattern,
                 output_pattern = arguments.output_pattern,
                 results_prefix = arguments.results_prefix,
                 mesh_prefix = arguments.mesh_prefix,
                 batch_size = arguments.batch_size,
                 verbose = arguments.verbose)
