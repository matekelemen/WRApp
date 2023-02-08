"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp
from ..WRAppClass import WRAppClass

# --- STD Imports ---
import abc


class SnapshotIO(WRAppClass):
    """@brief Interface for writing/loading snapshots to/from disk."""

    def __call__(self, model_part: KratosMultiphysics.ModelPart) -> None:
        self._GetOperation(model_part).Execute()


    @abc.abstractmethod
    def ReadID(self) -> WRApp.CheckpointID:
        """@brief Read data from a file that identifies a @ref Snapshot.
           @returns (STEP, ANALYSIS_PATH)"""
        return WRApp.CheckpointID()


    @classmethod
    @abc.abstractmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        raise RuntimeError("Attempt to call a pure virtual function")


    @abc.abstractmethod
    def _GetOperation(self, model_part: KratosMultiphysics.ModelPart) -> KratosMultiphysics.Operation:
        """@brief Get the IO operation to execute on the provided @ref ModelPart."""
        return KratosMultiphysics.Operation()
