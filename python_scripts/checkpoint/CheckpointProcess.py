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


## @addtogroup WRApplication
## @{
## @addtogroup checkpointing
## @{


class CheckpointSelector(WRApp.WRAppClass):
    """ @brief A functor taking a @ref Model and returning a @ref CheckpointID to load or @a None.
        @classname CheckpointSelector
        @note A C++ bound selector should return an @a std::optional<CheckpointID>.
    """

    def __init__(self, *args):
        super().__init__()

    @abc.abstractmethod
    def __call__(self, model: KratosMultiphysics.Model) -> typing.Union[WRApp.CheckpointID,None]:
        pass



class DefaultCheckpointSelector(CheckpointSelector):
    """ @brief Always returns @a None, i.e. never loads checkpoints.
        @classname DefaultCheckpointSelector
    """

    def __init__(self, *args):
        super().__init__(*args)


    def __call__(self, model: KratosMultiphysics.Model) -> None:
        return None



class CheckpointProcess(KratosMultiphysics.Process, WRApp.WRAppClass, metaclass = WRApp.WRAppMeta):
    """ @brief Main interface process for checkpointing.
        @classname CheckpointProcess
        @details @ref CheckpointProcess optionally executes load operations in @ref ExecuteInitializeSolutionStep and
                  write operations in @ref ExecuteFinalizeSolutionStep. The process itself implements minimal logic and
                  defers the execution of tasks to the following components:
                  - <em>IO Format</em> : The checkpointing format can be configured via the "snapshot_type" subparameter
                                         in the input parameters, which must refer to a valid implementation of @ref Snapshot
                                         that is accessible from the @ref Registry. Check out @ref HDF5Snapshot for a reference
                                         implementation. The checkpoint system can be configured by specifying the "snapshot_parameters"
                                         subparameter in the input parameters, that gets forwarded to the selected snapshot's
                                         @ref Snapshot.Manager. The default settings configure HDF5 input/output that covers all
                                         nodal, element, and condition variables and flags, as well as the entire @ref ProcessInfo.
                  - <em>Output control</em>: a @ref ModelPredicate that decides whether a snapshot should be written
                                             based on the current state of the input model. The predicate type must be
                                             accessible from the @ref Registry, and can be configured via the
                                             <em>"write_predicate"</em> subparameter in the input parameters.
                                             @code
                                             "write_predicate" : {
                                                "type" : "name-of-the-predicate-type-in-the-registry",
                                                "parameters" : {<parameters-passed-to-the-predicate-instance>}
                                             }
                                             @endcode
                                             The default behaviour is writing a snapshot at each time step.
                  - <em>Input control</em>: a callable with the following signature:
                                            @code std::optional<WRApp::CheckpointID> (const Model&) @endcode
                                            that decides whether a checkpoint should be loaded, and if yes, which
                                            one; based on the current state of the provided model.
                                            The callable type must be accessible through the @ref Registry, and
                                            can be configured via the <em>"checkpoint_selector"</em> subparameter
                                            in the input parameters.
                                            @code
                                            "checkpoint_selector" : {
                                                "type" : "name-of-the-callable-type-in-the-registry",
                                                "parameters" : {<parameters-passed-to-the-callable-instance>}
                                            }
                                            @endcode
                                            The default behaviour is never to load any checkpoints.
                  Default parameters:
                  @code
                  {
                      "model_part_name" : "",
                      "snapshot_type" : "WRApplication.Snapshot.SnapshotFS.HDF5Snapshot",
                      "snapshot_parameters" : {...},
                      "write_predicate" : {
                          "type" : "WRApplication.ConstModelPredicate",
                          "parameters" : [{"value" : true}]
                      },
                      "checkpoint_selector" : {
                          "type" : "WRApplication.CheckpointSelector.DefaultCheckpointSelector",
                          "parameters" : []
                      }
                  }
                  @endcode
        @note This process should only be constructed <b>after</b> the mesh was loaded, and all variables
              (historical/non-historical nodal, element, condition, process info) were added in the target
              @ref ModelPart. Although new @ref Snapshot implementations can be added that relax this requirement,
              all current implementations assume that the topology of the mesh does not change throughout the
              analysis, and no variables are added/removed to/from any component in the subject @ref ModelPart.
        @note The default implementation assumes that the list of (non-historical) variables is uniform within
              component types of the @ref ModelPart (eg: all elements have the exact same list of variables).
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
            "snapshot_type" : "WRApplication.Snapshot.SnapshotFS.HDF5Snapshot",
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


## @}
## @}


def Factory(parameters: KratosMultiphysics.Parameters,
            model: KratosMultiphysics.Model) -> "CheckpointProcess":
    return CheckpointProcess(model, parameters)

