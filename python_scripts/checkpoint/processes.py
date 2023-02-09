"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp
from ..WRAppClass import WRAppClass
from .Snapshot import Snapshot
from .Checkpoint import Checkpoint

# --- STD Imports ---
import abc
import typing


class CheckpointSelector(WRAppClass):
    """@brief A functor taking a @ref Model and returning a @ref CheckpointID to load or @a None.
       @note A C++ bound selector should return an @a std::optional<CheckpointID>."""

    def __init__(self, _: KratosMultiphysics.Parameters):
        pass

    @abc.abstractmethod
    def __call__(self, model: KratosMultiphysics.Model) -> typing.Union[WRApp.CheckpointID,None]:
        pass



class DefaultCheckpointSelector(CheckpointSelector):
    """@brief Always returns @a None, i.e. never loads checkpoints."""

    def __init__(self, parameters: KratosMultiphysics.Parameters):
        super().__init__(parameters)


    def __call__(self, model: KratosMultiphysics.Model) -> None:
        return None



# Resolve metaclass conflicts
if type(KratosMultiphysics.Process) != type(abc.ABC):
    class ProcessABC(type(abc.ABC), type(KratosMultiphysics.Process)): pass
else:
    class ProcessABC(type(KratosMultiphysics.Process)): pass



class CheckpointProcess(KratosMultiphysics.Process):
    """ @brief Main interface process for checkpointing.
        """

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())
        self.__model = model
        self.__model_part = self.__model.GetModelPart(parameters["model_part_name"].GetString())

        # Snapshot setup
        snapshot_type: typing.Type[Snapshot] = KratosMultiphysics.Registry[parameters["snapshot_type"].GetString()]
        manager_type = snapshot_type.GetManagerType()
        self.__snapshot_manager = manager_type(self.__model_part, parameters["snapshot_parameters"])

        # Construct predicates
        self.__write_predicate: typing.Callable[[KratosMultiphysics.Model],bool] = KratosMultiphysics.Registry[parameters["write_predicate"]["type"]](
            parameters["write_predicate"]["parameters"])
        self.__checkpoint_selector: CheckpointSelector = KratosMultiphysics.Registry[parameters["checkpoint_selector"]["type"]](
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
            "snapshot_type" : "Snapshot.HDF5Snapshot",
            "snapshot_parameters" : {},
            "write_predicate" : {
                "type" : "PipedModelPredicate.ConstModelPredicate",
                "parameters" : [
                    {"value" : true}
                ]
            },
            "checkpoint_selector" : {
                "type" : "CheckpointSelector.DefaultCheckpointSelector",
                "parameters" : []
            }
        }""")

        # Populate nested defaults
        snapshot_type: typing.Type[Snapshot] = KratosMultiphysics.Registry[output["snapshot_type"].GetString()]
        manager_type = snapshot_type.GetManagerType()
        output["snapshot_parameters"] = manager_type.GetDefaultParameters()

        return output



def Factory(parameters: KratosMultiphysics.Parameters,
            model: KratosMultiphysics.Model) -> "CheckpointProcess":
    return CheckpointProcess(model, parameters)
