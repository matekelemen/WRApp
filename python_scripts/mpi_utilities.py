"""@author Máté Kelemen"""

__all__ = ["MPIUnion"]

# --- Core Imports ---
import KratosMultiphysics

# --- WRApplication Imports ---
from KratosMultiphysics import WRApplication as WRApp


def MPIUnion(container: "set[str]", data_communicator: KratosMultiphysics.DataCommunicator) -> set:
    return set(WRApp.MPIAllGatherVStrings(list(container), data_communicator))
