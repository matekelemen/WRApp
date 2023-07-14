"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp
from .Snapshot import Snapshot, SnapshotManager
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
                  - <em>IO Format</em> : The checkpointing format can be configured via the @a "snapshot_type" subparameter
                                         in the input parameters, which must refer to a valid implementation of @ref Snapshot
                                         that is accessible from the @ref RuntimeRegistry. Check out @ref HDF5Snapshot for a reference
                                         implementation. The checkpoint system can be configured by specifying the @a "snapshot_parameters"
                                         subparameter in the input parameters, that gets forwarded to the selected snapshot's
                                         @ref SnapshotManager. The default settings configure HDF5 input/output that covers all
                                         nodal, element, and condition variables and flags, as well as the entire @ref ProcessInfo.
                  - <em>Output control</em>: a @ref ModelPredicate that decides whether a snapshot should be written
                                             based on the current state of the input @ref Model. The predicate type must be
                                             accessible from the @ref RuntimeRegistry, and can be configured via the
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
                                            one; based on the current state of the provided @ref Model.
                                            The callable type must be accessible through the @ref RuntimeRegistry, and
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

        default_parameters = self.GetDefaultParameters()
        if not parameters.Has("model_part_name"):
            parameters.ValidateAndAssignDefaults(default_parameters) # <== throws an exception with a more informative message
        self.__model = model
        self.__model_part = self.__model.GetModelPart(parameters["model_part_name"].GetString())
        self.__parameters = parameters

        # Populate nested default parameters
        snapshot_type: typing.Type[Snapshot] = WRApp.GetRegisteredClass(self.__parameters["snapshot_type"].GetString())
        manager_type = snapshot_type.GetManagerType()
        self.__parameters["snapshot_parameters"].ValidateAndAssignDefaults(manager_type.GetDefaultParameters())

        # Declarations to be defined in Initialize
        self.__snapshot_manager: SnapshotManager
        self.__write_predicate: WRApp.ModelPredicate
        self.__checkpoint_selector: CheckpointSelector


    def Initialize(self) -> None:
        default_parameters = self.GetDefaultParameters()

        # Construct default parameters, collecting all variables
        # and flags from the specified model part
        nodal_historical_variables = WRApp.MPIUtils.ExtractNodalSolutionStepDataNames(self.__model_part)
        nodal_variables = WRApp.MPIUtils.ExtractNodalDataNames(self.__model_part)
        nodal_flags = WRApp.MPIUtils.ExtractNodalFlagNames(self.__model_part)
        element_variables = WRApp.MPIUtils.ExtractElementDataNames(self.__model_part)
        element_flags = WRApp.MPIUtils.ExtractElementFlagNames(self.__model_part)
        condition_variables = WRApp.MPIUtils.ExtractConditionDataNames(self.__model_part)
        condition_flags = WRApp.MPIUtils.ExtractConditionFlagNames(self.__model_part)

        default_parameters["snapshot_parameters"].AddValue("io", KratosMultiphysics.Parameters())
        for io_name in ("input_parameters", "output_parameters"):
            default_parameters["snapshot_parameters"]["io"].AddValue(io_name, KratosMultiphysics.Parameters())
            io_parameters = default_parameters["snapshot_parameters"]["io"][io_name]
            io_parameters.AddStringArray("nodal_historical_variables", nodal_historical_variables)
            io_parameters.AddStringArray("nodal_variables", nodal_variables)
            io_parameters.AddStringArray("nodal_flags", nodal_flags)
            io_parameters.AddStringArray("element_variables", element_variables)
            io_parameters.AddStringArray("element_flags", element_flags)
            io_parameters.AddStringArray("condition_variables", condition_variables)
            io_parameters.AddStringArray("condition_flags", condition_flags)

        self.__parameters.RecursivelyAddMissingParameters(default_parameters)

        # Snapshot setup
        snapshot_type: typing.Type[Snapshot] = WRApp.GetRegisteredClass(self.__parameters["snapshot_type"].GetString())
        manager_type = snapshot_type.GetManagerType()
        self.__snapshot_manager = manager_type(self.__model_part, self.__parameters["snapshot_parameters"])

        # Construct flow logic functors
        self.__write_predicate = WRApp.RegisteredClassFactory(
            self.__parameters["write_predicate"]["type"].GetString(),
            self.__parameters["write_predicate"]["parameters"]
        )

        self.__checkpoint_selector = WRApp.RegisteredClassFactory(
            self.__parameters["checkpoint_selector"]["type"].GetString(),
            self.__parameters["checkpoint_selector"]["parameters"]
        )


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
        self.__snapshot_manager.EraseObsolete()


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
        return output


## @}
## @}


def Factory(parameters: KratosMultiphysics.Parameters,
            model: KratosMultiphysics.Model) -> "CheckpointProcess":
    return CheckpointProcess(model, parameters)

