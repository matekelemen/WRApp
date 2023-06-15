""" @author Máté Kelemen"""

__all__ = [
    "SnapshotInMemory",
    "SnapshotInMemoryManager"
]

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
from .Snapshot import Snapshot, SnapshotManager
from .SnapshotInMemoryIO import SnapshotInMemoryInput, SnapshotInMemoryOutput
from KratosMultiphysics import WRApplication as WRApp

# --- STD Imports ---
import typing


## @addtogroup WRApplication
## @{
## @addtogroup checkpointing
## @{


class SnapshotInMemory(Snapshot):
    """ @brief @ref Snapshot that stores/fetches its data in/from memory.
        @classname SnapshotInMemory
    """

    def __init__(self,
                 id: WRApp.CheckpointID,
                 parameters: KratosMultiphysics.Parameters):
        super().__init__(id, parameters)


    def Exists(self) -> bool:
        # Return true if there's a match for CheckPointIDs regardless of model part names
        return bool(self.GetInputType().Glob(lambda pair: pair[1] == self.id))


    def IsValid(self) -> bool:
        return self.Exists()


    @staticmethod
    def GetInputType() -> typing.Type[SnapshotInMemoryInput]:
        return SnapshotInMemoryInput


    @staticmethod
    def GetOutputType() -> typing.Type[SnapshotInMemoryOutput]:
        return SnapshotInMemoryOutput


    @classmethod
    def GetManagerType(cls) -> typing.Type["SnapshotInMemoryManager"]:
        return SnapshotInMemoryManager



class SnapshotInMemoryManager(SnapshotManager):

    def __init__(self,
                 model_part: KratosMultiphysics.ModelPart,
                 parameters: KratosMultiphysics.Parameters):
        super().__init__(model_part, parameters)

        # Set the extractor for the internal journal
        def extractor(model: KratosMultiphysics.Model) -> KratosMultiphysics.Parameters:
            output = KratosMultiphysics.Parameters()
            local_model_part = model.GetModelPart(model_part.Name)
            process_info = local_model_part.ProcessInfo
            output.AddString("model_part_name", local_model_part.Name)
            output.AddInt("step", process_info[KratosMultiphysics.STEP])
            output.AddInt("analysis_path", process_info[WRApp.ANALYSIS_PATH])
            return output
        self._journal.SetExtractor(extractor)


    def Erase(self, id: WRApp.CheckpointID) -> None:
        erase_keys = [key for key, value in SnapshotInMemoryOutput._cache if value["id"] == id]
        for key in erase_keys:
            SnapshotInMemoryOutput.Erase(key)


    @classmethod
    def _IDFromEntry(cls, journal_entry: KratosMultiphysics.Parameters) -> WRApp.CheckpointID:
        return WRApp.CheckpointID(journal_entry["step"].GetInt(), journal_entry["analysis_path"].GetInt())


    @classmethod
    def _GetSnapshotType(cls) -> typing.Type[Snapshot]:
        return SnapshotInMemory


## @}
## @}
