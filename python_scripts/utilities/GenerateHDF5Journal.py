""" @author Máté Kelemen"""

__all__ = [
    "GenerateHDF5Journal"
]

# --- External Imports ---
import h5py

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
from KratosMultiphysics import WRApplication as WRApp

# --- STD Imports ---
import typing
import json
import re
import pathlib


def ExtractTimeLabel(placeholders: "dict[str,list[str]]", fallback: typing.Union[int,float]) -> typing.Union[int,float]:
    if "<step>" in placeholders:
        return int(placeholders["<step>"][0])
    elif "<time>" in placeholders:
        return float(placeholders["<time>"][0])
    return fallback



class HDF5Path:
    """ @brief Filesystem path to an HDF5 file and a prefix within, uniquely identifying dataset/group.
        @classname HDF5Path
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


    def __lt__(self, right: "HDF5Path") -> bool:
        return self.label < right.label


    def __eq__(self, right: "HDF5Path") -> bool:
        return self.label == right.label


    def __le__(self, right: "HDF5Path") -> bool:
        return self.label < right.label or self.label == right.label



def GlobHDF5(pattern: WRApp.ModelPartPattern,
             file: h5py.File,
             verbose = False) -> "list[str]":
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
                if verbose:
                    print(f"processing {path}{'/' if path != '/' else ''}{item}")
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
    input_pattern = WRApp.ModelPartPattern(input_file_pattern)
    results_pattern = WRApp.ModelPartPattern(results_prefix)
    mesh_pattern = WRApp.ModelPartPattern(mesh_prefix)

    with open(output_path, "w") as journal:
        for file_path, file_placeholders in sorted(((path, input_pattern.Match(str(path))) for path in input_pattern.Glob()), key = InputFileOrdering):
            with h5py.File(file_path, "r") as file:
                results = sorted(
                    HDF5Path(file_path,
                             file_placeholders,
                             prefix,
                             results_pattern.Match(prefix))
                    for prefix in GlobHDF5(results_pattern, file, verbose = verbose))
                meshes = sorted(
                    HDF5Path(file_path,
                             file_placeholders,
                             prefix,
                             mesh_pattern.Match(prefix))
                    for prefix in GlobHDF5(mesh_pattern, file, verbose = verbose))
            while results or meshes:
                current_results: typing.Optional[HDF5Path] = results.pop(0) if results else None

                # Check whether there's a mesh corresponding to the current results
                current_mesh: typing.Optional[HDF5Path] = None
                if current_results is not None:
                    for mesh in meshes:
                        if mesh <= current_results:
                            current_mesh = mesh
                        else:
                            break
                elif meshes:
                    current_mesh = meshes.pop(0)
                else:
                    break

                entry = dict()
                if current_results is not None:
                    entry["results"] = {
                        "file_name" : str(current_results.file_path),
                        "prefix" : str(current_results.prefix)
                    }

                if current_mesh is not None:
                    entry["mesh"] = {
                        "file_name" : str(current_mesh.file_path),
                        "prefix" : str(current_mesh.prefix)
                    }

                journal.write(json.dumps(entry))
                journal.write("\n")



class GenerateHDF5Journal(WRApp.WRAppClass, KratosMultiphysics.Operation):
    """ @brief Generate a @ref Kratos::Journal from globbed HDF5 results.
        @classname GenerateHDF5Journal
    """

    def __init__(self,
                 _: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        WRApp.WRAppClass.__init__(self)
        KratosMultiphysics.Operation.__init__(self)
        self.__parameters = parameters
        self.__parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())


    def Execute(self) -> None:
        MakeJournal(self.__parameters["file_name"].GetString(),
                    self.__parameters["results_prefix"].GetString(),
                    self.__parameters["mesh_prefix"].GetString(),
                    self.__parameters["journal_name"].GetString(),
                    verbose = self.__parameters["verbose"].GetBool())


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters("""{
            "file_name" : "",
            "results_prefix" : "/ResultsData",
            "mesh_prefix" : "/ModelData",
            "journal_name" : "hdf5_output.jrn",
            "verbose" : false
        }""")



WRApp.CLI.AddOperation(GenerateHDF5Journal)
