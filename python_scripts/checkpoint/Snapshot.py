"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics
from KratosMultiphysics.kratos_utilities import DeleteFileIfExisting

# --- WRApplication Imports ---
from KratosMultiphysics import WRApplication as WRApp
from KratosMultiphysics.WRApplication import CheckpointPattern
from .SnapshotIO import SnapshotIO

# --- Core Imports ---
import abc
import typing
import pathlib
import inspect


## @addtogroup WRApplication
## @{
## @addtogroup checkpointing
## @{


class Snapshot(WRApp.WRAppClass):
    """ @brief Class representing a snapshot of a @ref ModelPart state.
        @classname Snapshot
        @details A snapshot is uniquely defined by its path ID and step index
                 for a specific analysis. The path ID indicates how many times
                 the solution loop jumped back and continued from an earlier @ref Checkpoint,
                 while the step index counts the number of steps since the analysis
                 began, disregarding steps that branched off the current analysis path.
        @note Specialized for keeping data in memory or on disk.
    """

    def __init__(self,
                 id: WRApp.CheckpointID,
                 parameters: KratosMultiphysics.Parameters):
        super().__init__()
        self._parameters = parameters
        self._parameters.RecursivelyValidateAndAssignDefaults(self.GetDefaultParameters())
        self.__id = id
        self._input = self.GetInputType()(self._parameters["input_parameters"])
        self._output = self.GetOutputType()(self._parameters["output_parameters"])


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
        return False


    @abc.abstractmethod
    def IsValid(self) -> bool:
        """@brief Check whether the stored data matches up the ID of the @ref Snapshot."""
        return False


    @staticmethod
    @abc.abstractmethod
    def GetInputType() -> typing.Type[SnapshotIO]:
        """ @brief Get the class responsible for reading snapshot data.
            @note Override this member if you need a custom read logic.
        """
        return SnapshotIO


    @staticmethod
    @abc.abstractmethod
    def GetOutputType() -> typing.Type[SnapshotIO]:
        """ @brief Get the class responsible for writing snapshot data.
            @note Override this member if you need a custom write logic.
        """
        return SnapshotIO


    @classmethod
    @abc.abstractmethod
    def GetManagerType(cls) -> typing.Type["SnapshotManager"]:
        """ @brief Return the manager type associated with the specialized @ref Snapshot type."""
        return SnapshotManager


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        """ @code
            {
                "input_parameters" : "default parameters for the input type",
                "output_parameters" : "default parameters for the output type"
            }
            @endcode
        """
        parameters = KratosMultiphysics.Parameters()
        parameters.AddValue("input_parameters", cls.GetInputType().GetDefaultParameters())
        parameters.AddValue("output_parameters", cls.GetOutputType().GetDefaultParameters())
        return parameters


    @staticmethod
    def GetSolutionPath(snapshots: list) -> list:
        """ @brief Pick snapshots from the provided list that are part of the solution path.
            @param snapshots: list of snapshots of the analysis.
            @return A sorted list of snapshots that make up the solution path.
            @details A path is assembled backtracking from the last snapshot, recreating the
                     solution path iff the input list contains the solution path. Otherwise
                     the assembled path is the one that has a dead-end at the last snapshot.
        """
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
                      parameters: KratosMultiphysics.Parameters) -> "Snapshot":
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
    """ @brief Class representing a snapshot of a @ref ModelPart state in memory (stores a deep copy of the model part).
        @classname SnapshotInMemory
        @todo Implement in-memory snapshots if necessary (@matekelemen).
    """
    pass



class SnapshotFS(Snapshot):
    """ @brief Class representing a snapshot of a @ref ModelPart state and its associated output file on the filesystem.
        @classname SnapshotFS
    """

    def __init__(self,
                 id: WRApp.CheckpointID,
                 parameters: KratosMultiphysics.Parameters):
        """ @copydoc Snapshot.__init__"""
        super().__init__(id, parameters)


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
    def FromFile(cls: typing.Type["SnapshotFS"],
                 parameters: KratosMultiphysics.Parameters) -> "SnapshotFS":
        """ @brief Construct a @ref Snapshot instance from a snapshot file.
            @param file_path: path to a snapshot file to parse.
            @param input_parameters: @ref Parameters to instantiate an input processor from.
            @param output_parameters: @ref Parameters to instantiate an output processor from.
        """
        parameters["input_parameters"].ValidateAndAssignDefaults(cls.GetIntputType().GetDefaultParameters())
        file_path = pathlib.Path(parameters["input_parameters"]["io_settings"]["file_path"].GetString())
        if file_path.is_file():
            input = cls.GetInputType()(parameters["input_parameters"])
            id = input.GetID()
            return cls(id, parameters)
        elif file_path.is_dir():
            raise FileExistsError(f"{file_path} is a directory")
        else:
            raise FileNotFoundError(f"File not found: {file_path}")


    @classmethod
    def FromModelPart(cls: typing.Type["SnapshotFS"],
                      model_part: KratosMultiphysics.ModelPart,
                      parameters: KratosMultiphysics.Parameters = None) -> "SnapshotFS":
        """@brief Deduce variables from an input @ref ModelPart and construct a @ref SnapshotFS.
           @details Input- and output parameters are defaulted if they are not specified by the user.
                    The related file name defaults to "<model_part_name>_step_<step>_path_<path>.h5"."""
        model_part_name = model_part.Name
        step = model_part.ProcessInfo[KratosMultiphysics.STEP]
        analysis_path = model_part.ProcessInfo[WRApp.ANALYSIS_PATH]

        if not parameters.Has("input_parameters"):
            parameters.AddValue("input_parameters", cls.GetInputType().GetDefaultParameters())
            parameters["input_parameters"]["io_settings"]["file_name"].SetString(f"{model_part_name}_step_{step}_path_{analysis_path}.h5")
        else:
            parameters["input_parameters"].ValidateAndAssignDefaults(cls.GetInputType().GetDefaultParameters())

        if not parameters.Has("output_parameters"):
            parameters.AddValue("output_parameters", cls.GetOutputType().GetDefaultParameters())
            parameters["output_parameters"]["io_settings"]["file_name"].SetString(f"{model_part_name}_step_{step}_path_{analysis_path}.h5")

        return cls(WRApp.CheckpointID(step, analysis_path), parameters)


    @classmethod
    def Collect(cls: typing.Type["SnapshotFS"],
                pattern: str,
                parameters: KratosMultiphysics.Parameters) -> list:
        """@brief Find and read all snapshot files that match the provided file name pattern.
           @param pattern: the file name pattern compatible with @ref CheckpointPattern to search for.
           @param parameters: @ref Parameters to instantiate the @ref Snapshot with.
           @return A list of @ref SnapsotFS loaded from discovered snapshot files, sorted in
                   ascending order (comparison is performed with respect to @ref CheckpointID).
        """
        # Assign default config
        if not parameters.Has("input_parameters"):
            parameters.AddValue("input_parameters", cls.GetInputType().GetDefaultParameters())
        else:
            parameters["input_parameters"].ValidateAndAssignDefaults(cls.GetInputType().GetDefaultParameters())

        if not parameters.Has("output_parameters"):
            parameters.AddValue("output_parameters", cls.GetOutputType().GetDefaultParameters())
        else:
            parameters["output_parameters"].ValidateAndAssignDefaults(cls.GetOutputType().GetDefaultParameters())
        snapshots = []

        for file_path in CheckpointPattern(pattern).Glob():
            tmp_parameters = parameters.Clone()
            tmp_parameters["input_parameters"]["io_settings"]["file_path"].SetString(str(file_path))
            tmp_parameters["output_parameters"]["io_settings"]["file_path"].SetString(str(file_path))
            snapshots.append(cls.FromFile(tmp_parameters))

        snapshots.sort()
        return snapshots



class SnapshotPredicate(WRApp.WRAppClass):
    """ @brief Base class for a predicate that takes a @ref CheckpointID.
        @classname SnapshotPredicate
    """

    @abc.abstractmethod
    def __call__(self, id: WRApp.CheckpointID) -> bool:
        """ @brief Evaluate the predicate."""
        pass



class NeverEraseSnapshots(SnapshotPredicate):
    """ @brief Always returns false.
        @classname NeverEraseSnapshots
    """

    def __call__(self, id: WRApp.CheckpointID) -> bool:
        return False



class SnapshotManager(metaclass = abc.ABCMeta):
    """ @brief Interface for @ref Snapshot lifetime management.
        @classname SnapshotManager
        @details @ref SnapshotManager supports adding, retrieving and erasing @ref Snapshot s.
                 Added (or discovered) snapshots are tracked via @ref Journal, and erased
                 based on the return value of a predicate (@ref CheckpointID -> @a bool)."""

    def __init__(self,
                    model_part: KratosMultiphysics.ModelPart,
                    parameters: KratosMultiphysics.Parameters):
        parameters.AddMissingParameters(self.GetDefaultParameters())
        self._parameters = parameters

        self._model_part = model_part
        self._journal = WRApp.Journal(pathlib.Path(parameters["journal_path"].GetString()))
        self.__check_duplicates = self._parameters["check_duplicates"].GetBool()

        # Instantiate the predicate (from registered class or instance)
        registered_item = KratosMultiphysics.Registry[parameters["erase_predicate"]["type"].GetString()]
        registered_class = registered_item if inspect.isclass(registered_item) else type(registered_item)
        self._predicate = registered_class(parameters["erase_predicate"]["parameters"])


    def Add(self, model_part: KratosMultiphysics.ModelPart) -> None:
        """ @brief Construct a snapshot and add it to the internal journal."""
        # Mutating operations on the journal can only be executed on the main rank
        if model_part.GetCommunicator().GetDataCommunicator().Rank() == 0:
            if self.__check_duplicates: # <== check whether a snapshot with the current ID exists
                id = WRApp.CheckpointID(model_part.ProcessInfo[KratosMultiphysics.STEP],
                                        model_part.ProcessInfo[WRApp.ANALYSIS_PATH])
                duplicate_entry = next((entry for entry in self._journal if id == self._IDFromEntry(entry)), None)
                if not (duplicate_entry is None):
                    raise RuntimeError(f"Duplicate snapshot ({id}) at {duplicate_entry['path'].GetString()}: {duplicate_entry['prefix'].GetString()}")

            # Recurd the new snapshot in the journal
            self._journal.Push(model_part.GetModel())

        # Construct and write the snapshot
        self._GetSnapshotType().FromModelPart(
            model_part,
            self._parameters["io"]
        ).Write(model_part)


    def Get(self, id: WRApp.CheckpointID) -> "Snapshot":
        """ @brief Retrieve a snapshot from the internal journal that matches the provided ID."""
        return self._GetSnapshotType()(id, self._parameters)


    @abc.abstractmethod
    def Erase(self, id: WRApp.CheckpointID) -> None:
        """ @brief Erase an entry from the internal journal that matches the provided ID and delete its related snapshot."""
        pass


    def EraseObsolete(self) -> None:
        """ @brief Call @ref Manager.Erase on all IDs that return true for the provided predicate."""
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
            if self._model_part.GetCommunicator().GetDataCommunicator().Rank() == 0:
                self._journal.EraseIf(predicate_wrapper)
            for id in erase_ids:
                self.Erase(id)


    @classmethod
    @abc.abstractmethod
    def _IDFromEntry(cls, journal_entry: KratosMultiphysics.Parameters) -> WRApp.CheckpointID:
        """ @brief Get the @ref CheckpointID from an entry in the internal @ref Journal."""
        pass


    @classmethod
    @abc.abstractmethod
    def _GetSnapshotType(cls) -> typing.Type[Snapshot]:
        return Snapshot


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        """ @code
            {
                "io" : {
                    "input_parameters" : {
                        "nodal_historical_variables" : [],
                        "nodal_variables" : [],
                        "nodal_flags" : [],
                        "element_variables" : [],
                        "element_flags" : [],
                        "condition_variables" : [],
                        "condition_flags" : []
                    },
                    "output_parameters" : {
                        "nodal_historical_variables" : [],
                        "nodal_variables" : [],
                        "nodal_flags" : [],
                        "element_variables" : [],
                        "element_flags" : [],
                        "condition_variables" : [],
                        "condition_flags" : []
                    }
                },
                "erase_predicate" : {
                    "type" : "WRApplication.SnapshotPredicate.NeverEraseSnapshots",
                    "parameters" : {}
                },
                "journal_path" : "snapshots.jrn",
                "check_duplicates" : false
            }
            @endcode
        """
        parameters = KratosMultiphysics.Parameters(R"""{
            "io" : {},
            "erase_predicate" : {
                "type" : "WRApplication.SnapshotPredicate.NeverEraseSnapshots",
                "parameters" : {}
            },
            "journal_path" : "snapshots.jrn",
            "check_duplicates" : false
        }""")
        parameters["io"] = cls._GetSnapshotType().GetDefaultParameters()
        return parameters


## @}
## @}
