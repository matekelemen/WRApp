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
import KratosMultiphysics.HDF5Application as HDF5
from KratosMultiphysics.HDF5Application.xdmf_utils import RenumberConnectivitiesForXdmf,    \
                                                          CreateXdmfSpatialGrid,            \
                                                          XdmfResults,                      \
                                                          TryOpenH5File,                    \
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
import xml.etree.ElementTree


def CreateXdmfTemporalGridFromMultifile(paths: "list[tuple[str,dict[str,list[str]]]]",
                                        mesh_prefix: str,
                                        results_prefix: str) -> TemporalGrid:
    temporal_grid = TemporalGrid()
    for path, placeholder_map in paths:
        with h5py.File(path, "r") as file_:
            if not file_:
                continue
            if mesh_prefix in file_:
                if not "Xdmf" in file_[mesh_prefix]:
                    continue
                sgrid = CreateXdmfSpatialGrid(file_[mesh_prefix])
            current_sgrid = SpatialGrid()
            for g in sgrid.grids:
                current_sgrid.add_grid(UniformGrid(g.name, g.geometry, g.topology))
            if results_prefix in file_:
                for result in XdmfResults(file_[results_prefix]):
                    current_sgrid.add_attribute(result)
            if "<time>" in placeholder_map:
                time_label = placeholder_map["<time>"][0]
            elif "<step>" in placeholder_map:
                time_label = placeholder_map["<step>"][0]
            else:
                time_label = "0.0"
            temporal_grid.add_grid(Time(time_label), current_sgrid)
    return temporal_grid


def GenerateXDMF(file_pattern: str,
                 mesh_prefix: str = "/ModelData",
                 results_prefix: str = "/ResultsData",
                 output_path: pathlib.Path = pathlib.Path("output.xdmf")) -> None:
    """ @brief Generate XDMF output for an existing set of HDF5 output files."""
    pattern = WRApp.ModelPartPattern(file_pattern)

    # Glob files and store their absolute paths along their matched placeholders.
    paths = sorted([(str(p.absolute()), pattern.Match(str(p))) for p in pattern.Glob()],
                   key = lambda pair: int(pair[1]["<step>"][0]))
    RenumberConnectivitiesForXdmf([pair[0] for pair in paths], mesh_prefix)
    temporal_grid = CreateXdmfTemporalGridFromMultifile(paths,
                                                        mesh_prefix,
                                                        results_prefix)
    domain = Domain(temporal_grid)
    xdmf = Xdmf(domain)
    xml.etree.ElementTree.ElementTree(xdmf.create_xml_element()).write(output_path)


class GenerateXDMFOperation(KratosMultiphysics.Operation, WRApp.WRAppClass):
    """ @brief """

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        KratosMultiphysics.Operation.__init__(self)
        WRApp.WRAppClass.__init__(self)
        self.__parameters = parameters
        self.__parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())


    def Execute(self) -> None:
        GenerateXDMF(self.__parameters["file_pattern"].GetString(),
                     mesh_prefix = self.__parameters["mesh_prefix"].GetString(),
                     results_prefix = self.__parameters["results_prefix"].GetString(),
                     output_path = pathlib.Path(self.__parameters["output_path"].GetString()))


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        """ @code
            {
                "file_pattern" : "",
                "mesh_prefix" : "/ModelData",
                "results_prefix" : "/ResultsData",
                "output_path" : "output.xdmf"
            }
            @endcode
        """
        return KratosMultiphysics.Parameters("""{
            "file_pattern": "",
            "mesh_prefix" : "/ModelData",
            "results_prefix" : "/ResultsData",
            "output_path" : "output.xdmf"
        }""")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser("generate-xdmf")

    parser.add_argument("file_pattern",
                        type = str,
                        help = "File path pattern to scan, compatible with ModelPartPattern.")
    parser.add_argument("-o",
                        "--output-path",
                        dest = "output_path",
                        type = pathlib.Path,
                        default = "output.xdmf",
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

    arguments = parser.parse_args()
    GenerateXDMF(arguments.file_pattern,
                 output_path = arguments.output_path,
                 results_prefix = arguments.results_prefix,
                 mesh_prefix = arguments.mesh_prefix)
