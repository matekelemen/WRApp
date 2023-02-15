"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp

# --- STD Imports ---
import abc
import pathlib


## @addtogroup WRApplication
## @{
## @addtogroup checkpointing
## @{


class SnapshotIO(WRApp.WRAppClass):
    """ @brief Interface for writing/loading snapshots to/from disk.
        @classname SnapshotIO
    """

    def __init__(self):
        super().__init__()


    def __call__(self, model_part: KratosMultiphysics.ModelPart) -> None:
        self._GetOperation(model_part).Execute()


    @abc.abstractmethod
    def GetID(self) -> WRApp.CheckpointID:
        """ @brief Read data from a file that identifies a @ref Snapshot."""
        return WRApp.CheckpointID()


    @abc.abstractmethod
    def GetPath(self, id: WRApp.CheckpointID = None) -> pathlib.Path:
        """ @brief Return the path to the associated file given the checkpoint ID, or the pattern if the ID is not provided."""
        pass


    @classmethod
    @abc.abstractmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        raise RuntimeError("Attempt to call a pure virtual function")


    @abc.abstractmethod
    def _GetOperation(self, model_part: KratosMultiphysics.ModelPart) -> KratosMultiphysics.Operation:
        """ @brief Get the IO operation to execute on the provided @ref ModelPart."""
        return KratosMultiphysics.Operation()


## @}
## @}
