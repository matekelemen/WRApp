"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics.KratosUnittest as UnitTest

# --- WRApp Imports ---
from KratosMultiphysics.WRApp.TestCase import SuiteFlags, TestSuite, TestCase

# STL imports
import pathlib


class TestLoader(UnitTest.TestLoader):
    @property
    def suiteClass(self):
        return TestSuite


def AssembleTestSuites(enable_mpi = False):
    """ Populates the test suites to run.

    Populates the test suites to run. At least, it should pupulate the suites:
    "small", "nighlty" and "all"

    Return
    ------

    suites: A dictionary of suites
        The set of suites with its test_cases added.
    """

    static_suites = UnitTest.KratosSuites

    # Test cases will be organized into lists first, then loaded into their
    # corresponding suites all at once.
    local_cases = {}
    for key in static_suites.keys():
        local_cases[key] = []

    # Glob all test cases in this application
    this_directory = pathlib.Path(__file__).absolute().parent
    test_loader = TestLoader()
    all_tests: "list[TestCase]" = test_loader.discover(this_directory, pattern = "*test*")

    # Sort globbed test cases into lists based on their suite flags
    #   flags correspond to entries in KratosUnittest.TestSuites
    #   (small, nightly, all, validation)
    #
    #   Cases with the 'mpi' flag are added to mpi suites as well as their corresponding normal suites.
    #   Cases with the 'mpi_only' flag are not added to normal suites.
    for test_case in all_tests:
        suite_flags = test_case.suite_flags.Copy()

        # Put test in 'all' if it isn't already there
        if not (suite_flags & SuiteFlags.ALL):
            suite_flags |= SuiteFlags.ALL

        # Add case to the corresponding suites
        for suite_name in suite_flags.GetNames():
            local_cases[suite_name].append(test_case)

    # Load all sorted cases into the global suites
    for suite_name, test_cases in local_cases.items():
        if enable_mpi:
            if "mpi" in suite_name:
                static_suites[suite_name].addTests(test_cases)
        else:
            if not ("mpi" in suite_name):
                static_suites[suite_name].addTests(test_cases)

    return static_suites


def Run(enable_mpi = False):
    UnitTest.runTests(AssembleTestSuites(enable_mpi = enable_mpi))


if __name__ == "__main__":
    Run(enable_mpi = False)
