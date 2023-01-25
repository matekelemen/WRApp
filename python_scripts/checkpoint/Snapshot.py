"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics

# --- HDF5 Imports ---
from KratosMultiphysics.HDF5Application.core.utils import ParametersWrapper
from KratosMultiphysics.HDF5Application.core.file_io import OpenHDF5File
import KratosMultiphysics.HDF5Application.core.operations.model_part as Operations

# --- WRApp Imports ---
from KratosMultiphysics import WRApp
from KratosMultiphysics.WRApp import CheckpointPattern
from ..mpi_utilities import MPIUnion

# --- Core Imports ---
import abc
import typing
import pathlib


class Snapshot(abc.ABC):
    """@brief Class representing a snapshot of a @ref ModelPart state.
       @details A snapshot is uniquely defined by its path ID and step index
                for a specific analysis. The path ID indicates how many times
                the solution loop jumped back and continued from an earlier @ref Checkpoint,
                while the step index counts the number of steps since the analysis
                began, disregarding steps that branched off the current analysis path.
       @note Specialized for keeping data in memory or on disk.
    """

    def __init__(self, path_id: int, step: int):
        self.__path_id = path_id
        self.__step = step

    @abc.abstractmethod
    def Load(self, model_part: KratosMultiphysics.ModelPart) -> None:
        """@brief Load data from this snapshot to the specified model part."""
        pass

    @abc.abstractmethod
    def Write(self, model_part: KratosMultiphysics.ModelPart) -> None:
        """@brief Write data from the current state of the specified model part to the snapshot."""
        pass

    @staticmethod
    def GetSolutionPath(snapshots: list) -> list:
        """@brief Pick snapshots from the provided list that are part of the solution path.
           @param snapshots: list of snapshots of the analysis.
           @return A sorted list of snapshots that make up the solution path.
           @details A path is assembled backtracking from the last snapshot, recreating the
                    solution path iff the input list contains the solution path. Otherwise
                    the assembled path is the one that has a dead-end at the last snapshot."""
        solution_path = []

        # Assemble the reversed solution path
        if snapshots:
            snapshots = sorted(snapshots)[::-1]
            solution_path.append(snapshots.pop(0))

            while snapshots:
                last = solution_path[-1]
                current = snapshots.pop(0)

                if last.path_id == current.path_id: # last and current snapshots are on the same branch
                    solution_path.append(current)
                    continue
                else: # the last snapshot opened a new branch
                    # Looking for the snapshot with branch ID and
                    # step index strictly LOWER than those of the last snapshot.
                    if current.step < last.step:
                        solution_path.append(current)

        return solution_path[::-1]

    @property
    def path_id(self) -> int:
        return self.__path_id

    @property
    def step(self) -> int:
        return self.__step

    def __lt__(self, other: "Snapshot") -> bool:
        if self.__path_id == other.__path_id:
            return self.__step < other.__step
        else:
            return self.__path_id < other.__path_id

    def __gt__(self, other: "Snapshot") -> bool:
        if self.__path_id == other.__path_id:
            return self.__step > other.__step
        else:
            return self.__path_id > other.__path_id

    def __eq__(self, other: "Snapshot") -> bool:
        return not (self < other) and not (self > other)

    def __ne__(self, other: "Snapshot") -> bool:
        return not (self == other)

    def __str__(self) -> str:
        return f"Snapshot on path {self.path_id} and step {self.step}"

    def __repr__(self) -> str:
        return self.__str__()


class SnapshotInMemory(Snapshot):
    """@brief Class representing a snapshot of a @ref ModelPart state in memory (stores a deep copy of the model part).
       @todo Implement in-memory snapshots if necessary (@matekelemen).
    """
    pass


class SnapshotIOBase(abc.ABC):
    """@brief Base class with common functionality to writing/loading snapshots to/from disk."""

    def __init__(self, parameters: KratosMultiphysics.Parameters):
        self.__parameters = parameters
        self.__parameters.RecursivelyValidateAndAssignDefaults(self.GetDefaultParameters())

    def __call__(self, model_part: KratosMultiphysics.ModelPart) -> None:
        """@brief Execute all defined IO operations."""
        with OpenHDF5File(self.__parameters["io_settings"], model_part) as file:
            for operation in self._GetOperations(model_part):
                operation(model_part, file)

    def ReadStepAndPathID(self) -> "tuple[int,int]":
        model = KratosMultiphysics.Model()
        model_part = model.CreateModelPart("temporary")
        with OpenHDF5File(self.__GetInputParameters(), model_part) as file:
            Operations.ReadProcessInfo(self.__parameters["operation_settings"])(model_part, file)
        step = model_part.ProcessInfo[KratosMultiphysics.STEP]
        path_id = model_part.ProcessInfo[WRApp.ANALYSIS_PATH]
        return step, path_id

    @property
    def parameters(self) -> KratosMultiphysics.Parameters:
        return self.__parameters.Clone()

    @staticmethod
    def _ExtractNodalSolutionStepDataNames(model_part: KratosMultiphysics.ModelPart) -> "list[str]":
        data_communicator = model_part.GetCommunicator().GetDataCommunicator()
        local_names = model_part.GetHistoricalVariablesNames()
        output =  list(MPIUnion(set(local_names), data_communicator))
        return output

    @staticmethod
    def _ExtractNodalDataNames(model_part: KratosMultiphysics.ModelPart, check_mesh_consistency: bool = False) -> "list[str]":
        data_communicator = model_part.GetCommunicator().GetDataCommunicator()
        local_names = model_part.GetNonHistoricalVariablesNames(model_part.Nodes, check_mesh_consistency)
        output =  list(MPIUnion(set(local_names), data_communicator))
        return output

    @staticmethod
    def _ExtractNodalFlagNames(model_part: KratosMultiphysics.ModelPart) -> "list[str]":
        return KratosMultiphysics.KratosGlobals.Kernel.GetFlagNames()

    @staticmethod
    def _ExtractElementDataNames(model_part: KratosMultiphysics.ModelPart, check_mesh_consistency: bool = False) -> "list[str]":
        data_communicator = model_part.GetCommunicator().GetDataCommunicator()
        local_names = model_part.GetNonHistoricalVariablesNames(model_part.Elements, check_mesh_consistency)
        output =  list(MPIUnion(set(local_names), data_communicator))
        return output

    @staticmethod
    def _ExtractElementFlagNames(model_part: KratosMultiphysics.ModelPart) -> "list[str]":
        return KratosMultiphysics.KratosGlobals.Kernel.GetFlagNames()

    @staticmethod
    def _ExtractConditionDataNames(model_part: KratosMultiphysics.ModelPart, check_mesh_consistency: bool = False) -> "list[str]":
        data_communicator = model_part.GetCommunicator().GetDataCommunicator()
        local_names = model_part.GetNonHistoricalVariablesNames(model_part.Conditions, check_mesh_consistency)
        output =  list(MPIUnion(set(local_names), data_communicator))
        return output

    @staticmethod
    def _ExtractConditionFlagNames(model_part: KratosMultiphysics.ModelPart) -> "list[str]":
        return KratosMultiphysics.KratosGlobals.Kernel.GetFlagNames()

    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        parameters = KratosMultiphysics.Parameters(R"""{
            "operation_settings" : {
                "prefix" : "",
                "time_format" : "0.4f"
            }
        }""")
        parameters.AddValue("io_settings", cls.GetDefaultIOParameters())
        return parameters

    @abc.abstractstaticmethod
    def GetDefaultIOParameters() -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters()

    @abc.abstractmethod
    def _GetOperations(self, model_part: KratosMultiphysics.ModelPart) -> typing.Iterable:
        """@brief Get all operations to be performed on the input model part."""
        return []

    def __GetInputParameters(self) -> KratosMultiphysics.Parameters:
        """@brief Get IO parameters for reading a file regardless of whether the class is meant for reading or writing."""
        io_parameters = self.GetDefaultIOParameters()
        io_parameters["file_access_mode"].SetString("read_only")
        return io_parameters

    def __GetOutputParameters(self) -> KratosMultiphysics.Parameters:
        """@brief Get IO parameters for writing to a file regardless of whether the class is meant for reading or writing."""
        io_parameters = self.GetDefaultIOParameters()
        io_parameters["file_access_mode"].SetString("read_write")
        return io_parameters


class DefaultSnapshotOutput(SnapshotIOBase):
    """@brief Output class for writing most data in the model part to an HDF5 snapshot.
       @details Data written: - nodal solution step data
                              - nodal data value
                              - nodal flag
                              - element data value
                              - element flag
                              - condition data value
                              - condition flag
                              - process info
    """

    @staticmethod
    def GetDefaultIOParameters() -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters("""{
            "file_name" : "checkpoints/<model_part_name>_snapshot_<path_id>_<step>.h5",
            "file_access_mode" : "truncate",
            "echo_level" : 0
        }""")

    def _GetOperations(self, model_part: KratosMultiphysics.ModelPart) -> list:
        operations = []

        # Variables
        for operation, variable_names in ((Operations.NodalSolutionStepDataOutput, self._ExtractNodalSolutionStepDataNames(model_part)),
                                          (Operations.NodalDataValueOutput, self._ExtractNodalDataNames(model_part)),
                                          (Operations.NodalFlagValueOutput, self._ExtractNodalFlagNames(model_part)),
                                          (Operations.ElementDataValueOutput, self._ExtractElementDataNames(model_part)),
                                          (Operations.ElementFlagValueOutput, self._ExtractElementFlagNames(model_part)),
                                          (Operations.ConditionDataValueOutput, self._ExtractConditionDataNames(model_part)),
                                          (Operations.ConditionFlagValueOutput, self._ExtractConditionFlagNames(model_part))):
            parameters = self.parameters["operation_settings"]
            parameters.AddStringArray("list_of_variables", variable_names)
            operations.append(operation(ParametersWrapper(parameters)))

        # ProcessInfo
        operations.append(Operations.ProcessInfoOutput(ParametersWrapper(self.parameters["operation_settings"])))

        return operations


class DefaultSnapshotInput(SnapshotIOBase):
    """@brief Input class for reading most data from an HDF5 snapshot to a model part.
       @details Data read: - nodal solution step data
                           - nodal data value
                           - nodal flag
                           - element data value
                           - element flag
                           - condition data value
                           - condition flag
                           - process info
    """

    @staticmethod
    def GetDefaultIOParameters() -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters("""{
            "file_name" : "",
            "file_access_mode" : "read_only",
            "echo_level" : 0
        }""")

    def _GetOperations(self, model_part: KratosMultiphysics.ModelPart) -> list:
        operations = []

        # Variables
        for operation, variable_names in (
                                          (Operations.NodalSolutionStepDataInput, self._ExtractNodalSolutionStepDataNames(model_part)),
                                          (Operations.NodalDataValueInput, self._ExtractNodalDataNames(model_part)),
                                          (Operations.NodalFlagValueInput, self._ExtractNodalFlagNames(model_part)),
                                          (Operations.ElementDataValueInput, self._ExtractElementDataNames(model_part)),
                                          (Operations.ElementFlagValueInput, self._ExtractElementFlagNames(model_part)),
                                          (Operations.ConditionDataValueInput, self._ExtractConditionDataNames(model_part)),
                                          (Operations.ConditionFlagValueInput, self._ExtractConditionFlagNames(model_part))
                                          ):
            parameters = self.parameters["operation_settings"]
            parameters.AddStringArray("list_of_variables", variable_names)
            operations.append(operation(ParametersWrapper(parameters)))

        # ProcessInfo
        operations.append(Operations.ProcessInfoInput(ParametersWrapper(self.parameters["operation_settings"])))

        return operations


class SnapshotOnDisk(Snapshot):
    """@brief Class representing a snapshot of a @ref ModelPart state and its associated output file."""

    def __init__(self,
                 path_id: int,
                 step: int,
                 input_parameters: KratosMultiphysics.Parameters,
                 output_parameters: KratosMultiphysics.Parameters):
        """@brief Constructor.
           @param path_id: Lowest ID of the analysis path the snapshot belongs to.
           @param step: step index of the snapshot.
           @param input_parameters: @ref Parameters to instantiate an input processor from.
           @param output_parameters: @ref Parameters to instantiate an output processor from.
        """
        super().__init__(path_id, step)
        self.__input = self.GetInputType()(input_parameters)
        self.__output = self.GetOutputType()(output_parameters)

    def Write(self, model_part: KratosMultiphysics.ModelPart) -> None:
        self.__output(model_part)

    def Load(self, model_part: KratosMultiphysics.ModelPart) -> None:
        self.__input(model_part)

    @staticmethod
    def FromFile(input_parameters: KratosMultiphysics.Parameters,
                 output_parameters: KratosMultiphysics.Parameters) -> "SnapshotOnDisk":
        """@brief Construct a @ref Snapshot instance from a snapshot file.
           @param file_path: path to a snapshot file to parse.
           @param input_parameters: @ref Parameters to instantiate an input processor from.
           @param output_parameters: @ref Parameters to instantiate an output processor from.
        """
        input_parameters.ValidateAndAssignDefaults(SnapshotOnDisk.GetInputType().GetDefaultParameters())
        file_path = pathlib.Path(input_parameters["io_settings"]["file_path"].GetString())
        if file_path.is_file():
            input = SnapshotOnDisk.GetInputType()(input_parameters)
            step, path_id = input.ReadStepAndPathID()
            return SnapshotOnDisk(path_id, step, input_parameters, output_parameters)
        elif file_path.is_dir():
            raise FileExistsError(f"{file_path} is a directory")
        else:
            raise FileNotFoundError(f"File not found: {file_path}")

    @staticmethod
    def Collect(pattern: str,
                input_parameters: KratosMultiphysics.Parameters,
                output_parameters: KratosMultiphysics.Parameters) -> list:
        """@brief Find and read all snapshot files that match the provided file name pattern.
           @param pattern: the file name pattern compatible with @ref CheckpointPattern to search for.
           @param input_parameters: @ref Parameters to instantiate an input processor from.
           @param output_parameters: @ref Parameters to instantiate an output processor from.
           @return A list of @ref SnapsotOnDisk loaded from discovered snapshot files, sorted in
                   ascending order (comparison is performed lexicographically over {path_id, step_index}).
        """
        input_parameters.ValidateAndAssignDefaults(SnapshotOnDisk.GetInputType().GetDefaultParameters())
        output_parameters.ValidateAndAssignDefaults(SnapshotOnDisk.GetOutputTypye().GetDefaultParameters())
        snapshots = []

        for file_path in CheckpointPattern(pattern).Glob():
            current_input_parameters = input_parameters.Clone()
            current_output_parameters = output_parameters.Clone()
            current_input_parameters["io_settings"]["file_path"].SetString(str(file_path))
            current_output_parameters["io_settings"]["file_path"].SetString(str(file_path))
            snapshots.append(SnapshotOnDisk.FromFile(current_input_parameters, current_output_parameters))

        snapshots.sort()
        return snapshots

    @staticmethod
    def GetInputType() -> type:
        """@brief Get the class responsible for reading snapshot data.
           @note Override this member if you need a custom read logic.
        """
        return DefaultSnapshotInput

    @staticmethod
    def GetOutputType() -> type:
        """@brief Get the class responsible for writing snapshot data.
           @note Override this member if you need a custom write logic.
        """
        return DefaultSnapshotOutput
