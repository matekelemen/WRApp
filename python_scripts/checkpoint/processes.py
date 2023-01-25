"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics

# --- HDF5 Imports ---
import KratosMultiphysics.HDF5Application

# --- WRApp Imports ---
from KratosMultiphysics.WRApp.checkpoint.Snapshot import Snapshot

# --- STD Imports ---
import abc


# Resolve metaclass conflicts
if type(KratosMultiphysics.Process) != type(abc.ABC):
    class AbstractProcessMetaClass(type(abc.ABC), type(KratosMultiphysics.Process)):
        pass
else:
    class AbstractProcessMetaClass(type(KratosMultiphysics.Process)):
        pass


class CheckpointProcessBase(KratosMultiphysics.Process):

    def __init__(self, model: KratosMultiphysics.Model, parameters: KratosMultiphysics.Parameters):
        parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())
        self.parameters = parameters
        self.__model_part = model.GetModelPart(parameters["model_part_name"])
        self.__snapshot_type = KratosMultiphysics.Registry[parameters["checkpoint_settings"]["snapshot_settings"].GetString()]
        self.__condition = ImportUtility(parameters["checkpoint_settings"]["io_condition"])()

    @property
    def model_part(self) -> KratosMultiphysics.ModelPart:
        return self.__model_part

    @property
    def snapshot_type(self) -> type:
        return self.__snapshot_type

    def CheckCondition(self) -> bool:
        return self.__condition(self.model_part)

    def _GetCurrentPathID(self) -> int:
        """@brief Determine which analysis path is currently active."""
        # TODO

    @abc.abstractmethod
    def _CreateSnapshot(self) -> Snapshot:
        pass

    @staticmethod
    def GetDefaultParameters() -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters("""{
            "model_part_name" : "",
            "checkpoint_settings" : {
                "prefix" : "",
                "io_condition" : {
                    "import_module" : "KratosMultiphysics.WRApp.Checkpoint",
                    "import_name" : "ConstantCondition",
                    "value" : true
                },
                "snapshot_settings" : {
                    "import_module" : "KratosMultiphysics.WRApp.Checkpoint",
                    "import_name" : "SnapshotOnDisk",
                    "file_settings" : {
                        "file_name" : "checkpoints/<model_part_name>_snapshot_<path_id>_<step>.h5",
                        "file_access_mode" : "read_write",
                        "echo_level" : 0
                    }
                }
            }
        }""")


class CheckpointOutputProcess(KratosMultiphysics.OutputProcess, CheckpointProcessBase):
    """@brief A process for writing checkpoints."""

    def IsOutputStep(self) -> bool:
        return self.CheckCondition()

    def PrintOutput(self) -> None:
        self._CreateSnapshot().Write(self.model_part)

    def _CreateSnapshot(self) -> Snapshot:
        path_id = self._GetCurrentPathID()
        step = self.model_part.ProcessInfo[KratosMultiphysics.STEP]
        return self.snapshot_type(path_id, step, output_parameters = self.parameters["checkpoint_settings"]["snapshot_settings"]["file_settings"])

    @staticmethod
    def GetDefaultParameters() -> KratosMultiphysics.Parameters:
        parameters = CheckpointProcessBase.GetDefaultParameters()
        parameters["checkpoint_settings"]["snapshot_settings"]["file_settings"]["file_access_mode"].SetString("truncate")
        return parameters

