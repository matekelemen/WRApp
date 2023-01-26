"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics
from KratosMultiphysics import *

# --- WRApp Imports ---
from KratosMultiphysics.WRApp import *
from KratosMultiphysics.WRApp import TestCase


def Run():
    KratosMultiphysics.Tester.SetVerbosity(KratosMultiphysics.Tester.Verbosity.PROGRESS)
    KratosMultiphysics.Tester.RunTestSuite("KratosWRAppTestSuite")


class CppTests(TestCase.TestCase):

    def test_Cpp(self) -> None:
        Run()


if __name__ == '__main__':
    Run()
