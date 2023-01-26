"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics
from KratosMultiphysics import *

# --- WRApplication Imports ---
from KratosMultiphysics.WRApplication import *
from KratosMultiphysics.WRApplication import TestCase


def Run():
    KratosMultiphysics.Tester.SetVerbosity(KratosMultiphysics.Tester.Verbosity.PROGRESS)
    KratosMultiphysics.Tester.RunTestSuite("KratosWRApplicationTestSuite")


class CppTests(TestCase.TestCase):

    def test_Cpp(self) -> None:
        Run()


if __name__ == '__main__':
    Run()
