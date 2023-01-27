"""@author Máté Kelemen"""

# --- WRApp Imports ---
from .Snapshot import SnapshotOnDisk
from .HDF5SnapshotIO import HDF5SnapshotInput, HDF5SnapshotOutput

# --- STD Imports ---
import typing


class HDF5Snapshot(SnapshotOnDisk):
    """@brief Class representing a snapshot of a @ref ModelPart state and its associated output file in HDF5 format."""

    @staticmethod
    def GetInputType() -> typing.Type[HDF5SnapshotInput]:
        return HDF5SnapshotInput


    @staticmethod
    def GetOutputType() -> typing.Type[HDF5SnapshotOutput]:
        return HDF5SnapshotOutput
