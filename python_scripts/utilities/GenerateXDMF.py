""" @author Máté Kelemen"""

__all__ = [
    "GenerateXDMF"
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
from .GenerateHDF5Journal import HDF5Path

# --- STD Imports ---
import pathlib
import typing
import xml.etree.ElementTree
import multiprocessing
import os
import json



class _Dataset:
    """ @brief An @ref HDF5Path with an associated mesh, also represented by an @ref HDF5Path.
        @classname _Dataset
    """

    def __init__(self,
                 results: HDF5Path,
                 mesh: HDF5Path,
                 unique_mesh: bool):
        self.__results = results
        self.__mesh = mesh
        self.__unique_mesh = unique_mesh


    def HasUniqueMesh(self) -> bool:
        return self.__unique_mesh


    @property
    def results(self) -> HDF5Path:
        return self.__results


    @property
    def mesh(self) -> HDF5Path:
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



def MakeBatches(journal_path: pathlib.Path,
                output_path: str,
                batch_size: int = -1,
                verbose: bool = False) -> typing.Generator[_Batch,None,None]:
    if batch_size == 0:
        raise ValueError(f"Invalid batch size: {batch_size}")

    with open(journal_path, "r") as journal:
        datasets: "list[_Dataset]" = []
        current_mesh: typing.Optional[HDF5Path] = None
        output_pattern = WRApp.PlaceholderPattern(output_path,
                                                  {"<batch>" : WRApp.PlaceholderPattern.UnsignedInteger})
        i_batch = 0
        for entry in journal.readlines():
            map = json.loads(entry)

            # Get the mesh from the entry if it has one
            mesh = map.get("mesh", None)
            if mesh is not None:
                current_mesh = HDF5Path(pathlib.Path(mesh["file_name"]),
                                         {},
                                         mesh["prefix"],
                                         {})

            # Get results
            current_results = HDF5Path(pathlib.Path(map["results"]["file_name"]),
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
            RenumberConnectivitiesForXdmf([str(dataset.mesh.file_path)], dataset.mesh.prefix)
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



def BatchGenerate(arguments: "tuple[_Batch,bool]") -> None:
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



def Generate(journal_path: pathlib.Path,
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
            pool.map(BatchGenerate, ((batch, verbose) for batch in batches))
    else:
        for batch in batches:
            BatchGenerate((batch, verbose))



class GenerateXDMF(KratosMultiphysics.Operation, WRApp.WRAppClass):
    """ @brief Generate XDMF output for an existing set of HDF5 output files.
        @classname GenerateXDMF
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
                 _: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        KratosMultiphysics.Operation.__init__(self)
        WRApp.WRAppClass.__init__(self)
        self.__parameters = parameters
        self.__parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())
        self.__batch_size = parameters["batch_size"].GetInt()
        self.__output_pattern = parameters["output_pattern"].GetString()


    def Execute(self) -> None:
        Generate(pathlib.Path(self.__parameters["journal_path"].GetString()),
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



WRApp.CLI.AddOperation(GenerateXDMF)
