"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
import applications.WRApp.tests.test_WRApp as test_WRApp

# --- STD Imports ---
import sys


if __name__ == "__main__":
    if not KratosMultiphysics.IsDistributedRun():
        raise Exception("This test script can only be executed in MPI!")

    # Kratos tests are run in a rather cumbersome manner:
    # suite names get prepended with "_mpi" if "--using-mpi"
    # is passed through sys.argv, so it needs to be added if
    # the user hasn't done so (ouch).
    if not sys.argv[1:]:
        sys.argv.append("--using-mpi") # ;(

    test_WRApp.Run(enable_mpi = True)
