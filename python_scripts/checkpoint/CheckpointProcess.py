"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp
from .Snapshot import Snapshot
from .Checkpoint import Checkpoint

# --- STD Imports ---
import abc
import typing


class CheckpointSelector(WRApp.WRAppClass):
    """@brief A functor taking a @ref Model and returning a @ref CheckpointID to load or @a None.
       @note A C++ bound selector should return an @a std::optional<CheckpointID>."""

    def __init__(self, *args):
        super().__init__()

    @abc.abstractmethod
    def __call__(self, model: KratosMultiphysics.Model) -> typing.Union[WRApp.CheckpointID,None]:
        pass



class DefaultCheckpointSelector(CheckpointSelector):
    """@brief Always returns @a None, i.e. never loads checkpoints."""

    def __init__(self, *args):
        super().__init__(*args)


    def __call__(self, model: KratosMultiphysics.Model) -> None:
        return None



class CheckpointProcess(KratosMultiphysics.Process, WRApp.WRAppClass, metaclass = WRApp.WRAppMeta):
    """ @brief Main interface process for checkpointing.
        """

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        KratosMultiphysics.Process.__init__(self)
        WRApp.WRAppClass.__init__(self)
        parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())
        self.__model = model
        self.__model_part = self.__model.GetModelPart(parameters["model_part_name"].GetString())

        # Snapshot setup
        snapshot_type: typing.Type[Snapshot] = KratosMultiphysics.Registry[parameters["snapshot_type"].GetString()]["type"]
        manager_type = snapshot_type.GetManagerType()
        self.__snapshot_manager = manager_type(self.__model_part, parameters["snapshot_parameters"])

        # Construct logic functors
        predicate_type = KratosMultiphysics.Registry[parameters["write_predicate"]["type"].GetString()]["type"]
        self.__write_predicate: typing.Callable[[KratosMultiphysics.Model],bool] = predicate_type(
            parameters["write_predicate"]["parameters"])

        selector_type = KratosMultiphysics.Registry[parameters["checkpoint_selector"]["type"].GetString()]["type"]
        self.__checkpoint_selector: CheckpointSelector = selector_type(
            parameters["checkpoint_selector"]["parameters"])


    def ExecuteInitializeSolutionStep(self) -> None:
        """@brief Load data from a checkpoint if the checkpoint selector returns an ID."""
        checkpoint_id = self.__checkpoint_selector(self.__model)
        if checkpoint_id is not None:
            checkpoint_begin = checkpoint_id.GetStep() - self.__model_part.GetBufferSize() + 1
            checkpoint_end = checkpoint_id.GetStep() + 1
            snapshots: "list[Snapshot]" = []
            for step in range(checkpoint_begin, checkpoint_end):
                id = WRApp.CheckpointID(step, checkpoint_id.GetAnalysisPath())
                snapshots.append(self.__snapshot_manager.Get(id))

            Checkpoint(snapshots).Load(self.__model_part)


    def ExecuteFinalizeSolutionStep(self) -> None:
        """@brief Write a new snapshot if the write predicate returns true."""
        if self.__write_predicate(self.__model):
            self.__snapshot_manager.Add(self.__model_part)


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        output = KratosMultiphysics.Parameters(R"""{
            "model_part_name" : "",
            "snapshot_type" : "WRApplication.Snapshot.SnapshotOnDisk.HDF5Snapshot",
            "snapshot_parameters" : {},
            "write_predicate" : {
                "type" : "WRApplication.ConstModelPredicate",
                "parameters" : [
                    {"value" : true}
                ]
            },
            "checkpoint_selector" : {
                "type" : "WRApplication.CheckpointSelector.DefaultCheckpointSelector",
                "parameters" : []
            }
        }""")

        # Populate nested defaults
        snapshot_type: typing.Type[Snapshot] = KratosMultiphysics.Registry[output["snapshot_type"].GetString()]["type"]
        manager_type = snapshot_type.GetManagerType()
        output["snapshot_parameters"] = manager_type.GetDefaultParameters()

        return output



def Factory(parameters: KratosMultiphysics.Parameters,
            model: KratosMultiphysics.Model) -> "CheckpointProcess":
    return CheckpointProcess(model, parameters)
