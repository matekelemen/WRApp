""" @author Máté Kelemen"""

__all__ = [
    "GenerateXDMF"
]

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp
from .GenerateHDF5Journal import HDF5Path
import KratosMultiphysics.WRApplication.xdmf as XDMF

# --- STD Imports ---
import pathlib
from typing import Optional, Generator
import xml.etree.ElementTree
import json
import sys
from contextlib import ExitStack

# --- External Imports ---
try:
    import h5py
except ImportError:
    class GenerateXDMF(KratosMultiphysics.Process):
        def __init__(self, *args, **kwargs):
            super().__init__()
            raise ImportError(f"{type(self).__name__} requires h5py, which is not available")
else:
    class _Dataset:
        """ @brief An @ref HDF5Path with an associated mesh, also represented by an @ref HDF5Path.
            @classname _Dataset
        """

        def __init__(self,
                    results: Optional[HDF5Path],
                    mesh: HDF5Path,
                    unique_mesh: bool):
            self.__results = results
            self.__mesh = mesh
            self.__unique_mesh = unique_mesh


        def HasUniqueMesh(self) -> bool:
            return self.__unique_mesh


        @property
        def results(self) -> Optional[HDF5Path]:
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
                    verbose: bool = False) -> Generator[_Batch,None,None]:
        if batch_size == 0:
            raise ValueError(f"Invalid batch size: {batch_size}")

        with open(journal_path, "r") as journal:
            datasets: "list[_Dataset]" = []
            current_mesh: Optional[HDF5Path] = None
            current_results: Optional[HDF5Path] = None
            output_pattern = WRApp.PlaceholderPattern(output_path,
                                                      {"<batch>" : WRApp.PlaceholderPattern.UnsignedInteger})
            i_batch = 0
            for i_entry, entry in enumerate(journal.readlines()):
                map = json.loads(entry)

                # Get the mesh from the entry if it has one
                mesh = map.get("mesh", None)
                if mesh is not None:
                    current_mesh = HDF5Path(pathlib.Path(mesh["file_name"]),
                                            mesh["prefix"],
                                            {})

                # Get results
                results = map.get("results", None)
                if results is not None:
                    current_results = HDF5Path(pathlib.Path(map["results"]["file_name"]),
                                            map["results"]["prefix"],
                                            {})

                if current_mesh is None and current_results is None:
                    print(f"WARNING: no mesh or results were found in journal {journal_path} entry {entry} in line {i_entry}",
                        file = sys.stderr)
                    continue

                if current_mesh is None:
                    raise RuntimeError(f"Results in file '{current_results.file_path}' at '{current_results.prefix}' have no corresponding mesh")

                datasets.append(_Dataset(current_results,
                                        current_mesh,
                                        mesh is not None))

                if len(datasets) == batch_size:
                    yield _Batch(datasets, pathlib.Path(output_pattern.Apply({"<batch>" : str(i_batch)})))
                    datasets = []
                    i_batch += 1

        if datasets:
            yield _Batch(datasets, pathlib.Path(output_pattern.Apply({"<batch>" : str(i_batch)})))
        return



    def CreateXdmfTemporalGridFromMultifile(batch: _Batch, verbose: bool = False) -> XDMF.Grid:
        transient_grid = XDMF.GridCollection("Transient", XDMF.GridCollection.Type.Temporal)

        for i_dataset, dataset in enumerate(batch.datasets):
            grid: XDMF.Grid

            # Run a preprocessing operation for XDMF that generates index-based
            # connectivities from the ID-based system that Kratos uses.
            operation_parameters = KratosMultiphysics.Parameters()
            operation_parameters.AddString("file_path", str(dataset.mesh.file_path))
            operation_parameters.AddString("input_prefix", dataset.mesh.prefix)
            operation_parameters.AddString("output_prefix", dataset.mesh.prefix + "/Xdmf")
            operation_parameters.AddBool("overwrite", True)
            WRApp.Hdf5IndexConnectivitiesOperation(operation_parameters).Execute()

            # Get the file containing the mesh
            with ExitStack() as context_manager:
                mesh_file = h5py.File(dataset.mesh.file_path, "r")
                context_manager.enter_context(mesh_file)

                # Get the file containing the results,
                # but avoid trying to open the same file
                results_file: Optional[h5py.File] = None
                attribute_path: Optional[h5py.Group] = None
                if dataset.results is not None:
                    if dataset.results.file_path == dataset.mesh.file_path:
                        results_file = mesh_file
                    else:
                        results_file = h5py.File(dataset.results.file_path, "r")
                        context_manager.enter_context(results_file)
                    attribute_path = results_file[dataset.results.prefix]

                grid = XDMF.ParseMesh(mesh_file[dataset.mesh.prefix],
                                      attribute_path = attribute_path)

            grid.append(XDMF.TimePoint(i_dataset))
            transient_grid.append(grid)

        return transient_grid



    def BatchGenerate(arguments: "tuple[_Batch,bool]") -> None:
        """ @brief Generate an XDMF file from a batch of input files.
            @details The arguments are packaged into a single tuple:
                    - batch: Batch (batch to process)
                    - verbose: bool (print status messages while processing)
        """
        document = XDMF.Document()
        domain = XDMF.Domain()
        domain.append(CreateXdmfTemporalGridFromMultifile(*arguments))
        document.append(domain)

        xml.etree.ElementTree.ElementTree(document).write(arguments[0].output_path)



    def Generate(journal_path: pathlib.Path,
                    output_pattern: str = "batch_<batch>.xdmf",
                    batch_size: int = -1,
                    verbose: bool = False) -> None:
        """ @brief Generate XDMF output for an existing set of HDF5 output files."""
        batches = MakeBatches(journal_path,
                              output_pattern,
                              batch_size,
                              verbose = verbose)

        #thread_count = int(os.environ.get("OMP_NUM_THREADS", max([multiprocessing.cpu_count() - 1,1])))
        #if 1 < thread_count:
        #    with multiprocessing.Pool(thread_count) as pool:
        #        pool.map(BatchGenerate, ((batch, verbose) for batch in batches))
        #else:
        #    for batch in batches:
        #        BatchGenerate((batch, verbose))
        for batch in batches:
            BatchGenerate((batch, verbose))



    class GenerateXDMF(KratosMultiphysics.Operation, WRApp.WRAppClass):
        """ @brief Generate XDMF output for an existing set of HDF5 output files.
            @classname GenerateXDMF
            @details Default parameters:
                    @code
                    {
                        "journal_path": "",                         // <== path to the journal file containing output information
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
