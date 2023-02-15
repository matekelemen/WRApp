"""@author Máté Kelemen"""

__all__ = ["MPIUnion"]

# --- Core Imports ---
import KratosMultiphysics

# --- WRApplication Imports ---
from KratosMultiphysics import WRApplication as WRApp


## @addtogroup WRApplication
## @{
## @addtogroup utilities
## @{


def MPIUnion(container: "set[str]", data_communicator: KratosMultiphysics.DataCommunicator) -> "set[str]":
    """ @brief Return a union of strings across all MPI ranks."""
    return set(WRApp.MPIAllGatherVStrings(list(container), data_communicator))


## @}
## @}
