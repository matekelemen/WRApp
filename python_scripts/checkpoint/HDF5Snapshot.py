"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports --
import KratosMultiphysics.WRApplication as WRApp
from .Snapshot import SnapshotOnDisk
from .HDF5SnapshotIO import HDF5SnapshotInput, HDF5SnapshotOutput

# --- STD Imports ---
import typing


class HDF5Snapshot(SnapshotOnDisk):
    """@brief Class representing a snapshot of a @ref ModelPart state and its associated output file in HDF5 format."""

    def Erase(self, communicator: KratosMultiphysics.DataCommunicator) -> None:
        """@details Don't allow deleting the associated file if all snapshots are written into the same file."""
        is_single_file = all(io.GetPath() == io.GetPath(WRApp.CheckpointID(0,0)) for io in (self._input, self._output))
        if is_single_file:
            raise RuntimeError(f"Single file snapshots cannot be erased individually")
        super().Erase(communicator)


    @staticmethod
    def GetInputType() -> typing.Type[HDF5SnapshotInput]:
        return HDF5SnapshotInput


    @staticmethod
    def GetOutputType() -> typing.Type[HDF5SnapshotOutput]:
        return HDF5SnapshotOutput
