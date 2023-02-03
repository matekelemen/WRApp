"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics

# --- WRApplication Imports ---
import applications.WRApplication.tests.test_WRApplication as test_WRApplication

# --- STD Imports ---
import sys


if __name__ == "__main__":
    if not KratosMultiphysics.IsDistributedRun():
        raise Exception("This test script can only be executed in MPI!")

    # Kratos tests are run in a rather cumbersome manner:
    # suite names get prepended with "_mpi" if "--using-mpi"
    # is passed through sys.argv, so it needs to be added if
    # the user hasn't done so (ouch).
    if not "--using-mpi" in sys.argv:
        sys.argv.append("--using-mpi") # ;(

    test_WRApplication.Run(enable_mpi = True)
