"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics
from KratosMultiphysics import *

# --- WRApplication Imports ---
from KratosMultiphysics import WRApplication as WRApp
from KratosMultiphysics.WRApplication import *


def Run():
    KratosMultiphysics.Tester.SetVerbosity(KratosMultiphysics.Tester.Verbosity.PROGRESS)
    KratosMultiphysics.Tester.RunTestSuite("KratosWRApplicationTestSuite")


class CppTests(WRApp.TestCase):

    def test_Cpp(self) -> None:
        Run()


if __name__ == '__main__':
    Run()
