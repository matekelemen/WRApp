"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics
from KratosMultiphysics.kratos_utilities import DeleteFileIfExisting

# --- WRApplication Imports ---
from KratosMultiphysics import WRApplication as WRApp
from KratosMultiphysics.WRApplication import CheckpointPattern
from .SnapshotIO import SnapshotIO
from ..WRAppClass import WRAppClass

# --- Core Imports ---
import abc
import typing
import pathlib
import inspect


class Snapshot(WRAppClass):
    """@brief Class representing a snapshot of a @ref ModelPart state.
       @details A snapshot is uniquely defined by its path ID and step index
                for a specific analysis. The path ID indicates how many times
                the solution loop jumped back and continued from an earlier @ref Checkpoint,
                while the step index counts the number of steps since the analysis
                began, disregarding steps that branched off the current analysis path.
       @note Specialized for keeping data in memory or on disk.
    """

    def __init__(self, id: WRApp.CheckpointID):
        self.__id = id


    @abc.abstractmethod
    def Load(self, model_part: KratosMultiphysics.ModelPart) -> None:
        """@brief Load data from this snapshot to the specified model part."""
        pass


    @abc.abstractmethod
    def Write(self, model_part: KratosMultiphysics.ModelPart) -> None:
        """@brief Write data from the current state of the specified model part to the snapshot."""
        pass


    @abc.abstractmethod
    def Erase(self, communicator: KratosMultiphysics.DataCommunicator) -> None:
        """@brief Erase stored data related to this snapshot."""
        pass


    @abc.abstractmethod
    def Exists(self) -> bool:
        """@brief Check whether the data related to this @ref Snapshot has already been written."""
        pass


    @abc.abstractmethod
    def IsValid(self) -> bool:
        """@brief Check whether the stored data matches up the ID of the @ref Snapshot."""
        pass


    @classmethod
    @abc.abstractmethod
    def GetManagerType(cls) -> typing.Type["Manager"]:
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

                if last.analysis_path == current.analysis_path: # last and current snapshots are on the same branch
                    solution_path.append(current)
                    continue
                else: # the last snapshot opened a new branch
                    # Looking for the snapshot with branch ID and
                    # step index strictly LOWER than those of the last snapshot.
                    if current.step < last.step:
                        solution_path.append(current)

        return solution_path[::-1]


    @staticmethod
    @abc.abstractmethod
    def FromModelPart(model_part: KratosMultiphysics.ModelPart,
                      input_parameters: KratosMultiphysics.Parameters,
                      output_parameters: KratosMultiphysics.Parameters) -> "Snapshot":
        pass


    @property
    def analysis_path(self) -> int:
        return self.__id.GetAnalysisPath()


    @property
    def step(self) -> int:
        return self.__id.GetStep()


    @property
    def id(self) -> WRApp.CheckpointID:
        return self.__id


    def __lt__(self, other: "Snapshot") -> bool:
        return self.__id < other.__id


    def __gt__(self, other: "Snapshot") -> bool:
        return not (self < other)


    def __eq__(self, other: "Snapshot") -> bool:
        return self.__id == other.__id

    def __ne__(self, other: "Snapshot") -> bool:
        return not (self == other)


    def __str__(self) -> str:
        return f"Snapshot ({self.id})"


    def __repr__(self) -> str:
        return self.__str__()



class SnapshotInMemory(Snapshot):
    """@brief Class representing a snapshot of a @ref ModelPart state in memory (stores a deep copy of the model part).
       @todo Implement in-memory snapshots if necessary (@matekelemen).
    """
    pass



class SnapshotOnDisk(Snapshot):
    """@brief Class representing a snapshot of a @ref ModelPart state and its associated output file."""

    def __init__(self,
                 id: WRApp.CheckpointID,
                 input_parameters: KratosMultiphysics.Parameters,
                 output_parameters: KratosMultiphysics.Parameters):
        """@brief Constructor.
           @param path_id: Lowest ID of the analysis path the snapshot belongs to.
           @param step: step index of the snapshot.
           @param input_parameters: @ref Parameters to instantiate an input processor from.
           @param output_parameters: @ref Parameters to instantiate an output processor from.
        """
        super().__init__(id)
        self._input = self.GetInputType()(input_parameters)
        self._output = self.GetOutputType()(output_parameters)


    def Write(self, model_part: KratosMultiphysics.ModelPart) -> None:
        self._output(model_part)


    def Load(self, model_part: KratosMultiphysics.ModelPart) -> None:
        # Data in the ProcessInfo needs to be set before reading,
        # otherwise the IO class might look for the data in the
        # wrong place.
        model_part.ProcessInfo[KratosMultiphysics.STEP] = self.id.GetStep()
        model_part.ProcessInfo[WRApp.ANALYSIS_PATH] = self.id.GetAnalysisPath()
        self._input(model_part)

        # Check whether the correct snapshot was loaded
        new_id = WRApp.CheckpointID(model_part.ProcessInfo[KratosMultiphysics.STEP], model_part.ProcessInfo[WRApp.ANALYSIS_PATH])
        if new_id != self.id:
            raise RuntimeError(f"Snapshot attempted to load {self.id} but read {new_id} instead")


    def Erase(self, communicator: KratosMultiphysics.DataCommunicator) -> None:
        if communicator.Rank() == 0:
            for io in (self._input, self._output):
                DeleteFileIfExisting(str(io.GetPath(self.id)))


    def Exists(self) -> bool:
        return any(io.GetPath(self.id).exists() for io in (self._input, self._output))


    def IsValid(self) -> bool:
        if not self.Exists():
            raise FileNotFoundError(f"File associated to snapshot {self.id} not found: {self._input.GetPath(self.id)}")
        return self._input.GetID() == self.id


    @classmethod
    def FromFile(derived_class: typing.Type["SnapshotOnDisk"],
                 input_parameters: KratosMultiphysics.Parameters,
                 output_parameters: KratosMultiphysics.Parameters) -> "SnapshotOnDisk":
        """@brief Construct a @ref Snapshot instance from a snapshot file.
           @param file_path: path to a snapshot file to parse.
           @param input_parameters: @ref Parameters to instantiate an input processor from.
           @param output_parameters: @ref Parameters to instantiate an output processor from.
        """
        input_parameters.ValidateAndAssignDefaults(derived_class.GetInputType().GetDefaultParameters())
        file_path = pathlib.Path(input_parameters["io_settings"]["file_path"].GetString())
        if file_path.is_file():
            input = derived_class.GetInputType()(input_parameters)
            id = input.GetID()
            return derived_class(id, input_parameters, output_parameters)
        elif file_path.is_dir():
            raise FileExistsError(f"{file_path} is a directory")
        else:
            raise FileNotFoundError(f"File not found: {file_path}")


    @classmethod
    def FromModelPart(derived_class: typing.Type["SnapshotOnDisk"],
                      model_part: KratosMultiphysics.ModelPart,
                      input_parameters: KratosMultiphysics.Parameters = None,
                      output_parameters: KratosMultiphysics.Parameters = None) -> "SnapshotOnDisk":
        """@brief Deduce variables from an input @ref ModelPart and construct a @ref SnapshotOnDisk.
           @details Input- and output parameters are defaulted if they are not specified by the user.
                    The related file name defaults to "<model_part_name>_step_<step>_path_<path>.h5"."""
        model_part_name = model_part.Name
        step = model_part.ProcessInfo[KratosMultiphysics.STEP]
        analysis_path = model_part.ProcessInfo[WRApp.ANALYSIS_PATH]

        if input_parameters is None:
            input_parameters = derived_class.GetInputType().GetDefaultParameters()
            input_parameters["io_settings"]["file_name"].SetString(f"{model_part_name}_step_{step}_path_{analysis_path}.h5")

        if output_parameters is None:
            output_parameters = derived_class.GetOutputType().GetDefaultParameters()
            output_parameters["io_settings"]["file_name"].SetString(f"{model_part_name}_step_{step}_path_{analysis_path}.h5")

        return derived_class(WRApp.CheckpointID(step, analysis_path),
                             input_parameters,
                             output_parameters)


    @classmethod
    def Collect(derived_class: typing.Type["SnapshotOnDisk"],
                pattern: str,
                input_parameters: KratosMultiphysics.Parameters,
                output_parameters: KratosMultiphysics.Parameters) -> list:
        """@brief Find and read all snapshot files that match the provided file name pattern.
           @param pattern: the file name pattern compatible with @ref CheckpointPattern to search for.
           @param input_parameters: @ref Parameters to instantiate an input processor from.
           @param output_parameters: @ref Parameters to instantiate an output processor from.
           @return A list of @ref SnapsotOnDisk loaded from discovered snapshot files, sorted in
                   ascending order (comparison is performed lexicographically over {path_id, step_index}).
        """
        input_parameters.ValidateAndAssignDefaults(derived_class.GetInputType().GetDefaultParameters())
        output_parameters.ValidateAndAssignDefaults(derived_class.GetOutputType().GetDefaultParameters())
        snapshots = []

        for file_path in CheckpointPattern(pattern).Glob():
            current_input_parameters = input_parameters.Clone()
            current_output_parameters = output_parameters.Clone()
            current_input_parameters["io_settings"]["file_path"].SetString(str(file_path))
            current_output_parameters["io_settings"]["file_path"].SetString(str(file_path))
            snapshots.append(derived_class.FromFile(current_input_parameters, current_output_parameters))

        snapshots.sort()
        return snapshots


    @staticmethod
    @abc.abstractmethod
    def GetInputType() -> typing.Type[SnapshotIO]:
        """@brief Get the class responsible for reading snapshot data.
           @note Override this member if you need a custom read logic.
        """
        raise RuntimeError("Attempt to call a pure virtual function")


    @staticmethod
    @abc.abstractmethod
    def GetOutputType() -> typing.Type[SnapshotIO]:
        """@brief Get the class responsible for writing snapshot data.
           @note Override this member if you need a custom write logic.
        """
        raise RuntimeError("Attempt to call a pure virtual function")



class DefaultSnapshotErasePredicate(WRAppClass):
    def __call__(self, id: WRApp.CheckpointID) -> bool:
        return False



class Manager(metaclass = abc.ABCMeta):
    """@brief Interface for @ref Snapshot lifetime management.
        @details @ref Manager supports adding, retrieving and erasing @ref Snapshot s.
                 Added (or discovered) snapshots are tracked via @ref Journal, and erased
                 based on the return value of a predicate (@ref CheckpointID -> @a bool)."""

    def __init__(self,
                    model_part: KratosMultiphysics.ModelPart,
                    parameters: KratosMultiphysics.Parameters):
        parameters.AddMissingParameters(self.GetDefaultParameters())
        self._parameters = parameters
        self._model_part = model_part
        self._journal = WRApp.Journal(pathlib.Path(parameters["journal_path"].GetString()))

        # Instantiate the predicate (from registered class or instance)
        registered_item = KratosMultiphysics.Registry[parameters["erase_predicate"]["type"].GetString()]
        registered_class = registered_item if inspect.isclass(registered_item) else type(registered_item)
        self._predicate = registered_class(parameters["erase_predicate"]["parameters"])


    @abc.abstractmethod
    def Add(self, model_part: KratosMultiphysics.ModelPart) -> None:
        """@brief Construct a snapshot and add it to the internal journal."""
        pass


    @abc.abstractmethod
    def Get(self, id: WRApp.CheckpointID) -> "Snapshot":
        """@brief Retrieve a snapshot from the internal journal that matches the provided ID."""
        pass


    @abc.abstractmethod
    def Erase(self, id: WRApp.CheckpointID) -> None:
        """@brief Erase an entry from the internal journal that matches the provided ID and delete its related snapshot."""
        pass


    def EraseObsolete(self) -> None:
        """@brief Call @ref Manager.Erase on all IDs that return true for the provided predicate."""
        # Collect erased IDs into a list while erasing from the Journal
        erase_ids: "list[WRApp.CheckpointID]" = []
        def predicate_wrapper(entry: KratosMultiphysics.Parameters) -> bool:
            id = self._IDFromEntry(entry)
            result = self._predicate(id)
            if result:
                erase_ids.append(id)
            return result

        # Erase snapshots and the related journal entries
        if erase_ids:
            if self._model_part.GetCommunicator().GetDataCommunicator().GetRank() == 0:
                self._journal.EraseIf(predicate_wrapper)
            for id in erase_ids:
                self.Erase(id)


    @classmethod
    @abc.abstractmethod
    def _IDFromEntry(cls, journal_entry: KratosMultiphysics.Parameters) -> WRApp.CheckpointID:
        pass


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters(R"""{
            "erase_predicate" : {
                "type" : "DefaultSnapshotPredicate",
                "parameters" : {}
            },
            "journal_path" : "snapshots.jrn"
        }""")
