"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics.KratosUnittest as UnitTest


class _SuiteFlags:

    __names = (
        "ALL",
        "SMALL",
        "NIGHTLY",
        "VALIDATION",
        "MPI_ONLY",
        "NO_MPI"
    )


    def __init__(self, flags: int):
        self.__flags = flags


    def GetNames(self) -> "list[str]":
        """@brief Return a list of suite names that can be fed into the kratos test runner.
           @details Kratos distinguishes the following basic suites:
                    - small
                    - nightly
                    - all
                    - validation
                    Furthermore, it prepends them with "mpi_" if they're meant to be run with
                    MPI. By default, @ref _SuiteFlags casts SMALL, NIGHTLY, ALL, VALIDATION
                    to lower case and returns versions both with- and without "mpi_", unless
                    MPI_ONLY, or NO_MPI is set (MPI_ONLY only returns suites "mpi_*" while
                    NO_MPI only returns those without the prefix)."""
        return _SuiteFlags.__GetNames(self.__flags)


    @staticmethod
    def __GetNames(flags: int) -> "list[str]":
        mpi_only = flags & _SuiteFlags.FromSuiteName("MPI_ONLY").__flags
        no_mpi = flags & _SuiteFlags.FromSuiteName("NO_MPI").__flags

        # Unset MPI_ONLY and NO_MPI
        for flag in (mpi_only, no_mpi):
            flags ^= flag & flags

        if mpi_only and no_mpi:
            raise RuntimeError("Both 'MPI_ONLY' and 'NO_MPI' are set")

        suite_names = [name.lower() for index, name in enumerate(_SuiteFlags.__names) if flags & (1 << index)]
        mpi_suite_names = ["mpi_" + name for name in suite_names]

        if mpi_only:
            suite_names = mpi_suite_names
        elif no_mpi:
            pass
        else:
            suite_names += mpi_suite_names

        return suite_names


    def Copy(self) -> "_SuiteFlags":
        return _SuiteFlags(self.__flags)


    @staticmethod
    def FromSuiteName(suite_name: str) -> "_SuiteFlags":
        return _SuiteFlags(1 << _SuiteFlags.__names.index(suite_name))


    def __or__(self, right: "_SuiteFlags") -> "_SuiteFlags":
        return _SuiteFlags(self.__flags | right.__flags)


    def __ior__(self, right: "_SuiteFlags") -> "_SuiteFlags":
        self = self.__or__(right)
        return self

    def __and__(self, right: "_SuiteFlags") -> "_SuiteFlags":
        return _SuiteFlags(self.__flags & right.__flags)


    def __iand__(self, right: "_SuiteFlags") -> "_SuiteFlags":
        self = self.__and__(right)
        return self


    def __bool__(self) -> bool:
        flags = self.__flags
        mpi_only = flags & _SuiteFlags.FromSuiteName("MPI_ONLY").__flags
        no_mpi = flags & _SuiteFlags.FromSuiteName("NO_MPI").__flags

        # Unset MPI_ONLY and NO_MPI
        for flag in (mpi_only, no_mpi):
            flags ^= flag & flags

        return bool(self.__flags)


class SuiteFlags:
    SMALL       = _SuiteFlags.FromSuiteName("SMALL")
    NIGHTLY     = _SuiteFlags.FromSuiteName("NIGHTLY")
    VALIDATION  = _SuiteFlags.FromSuiteName("VALIDATION")
    MPI_ONLY    = _SuiteFlags.FromSuiteName("MPI_ONLY")
    NO_MPI      = _SuiteFlags.FromSuiteName("NO_MPI")
    ALL         = _SuiteFlags.FromSuiteName("ALL")


class TestCase(UnitTest.TestCase):
    """@brief Custom test case class for sorting cases into suites automatically while globbing."""

    suite_flags = SuiteFlags.ALL


class TestSuite(UnitTest.TestSuite):
    """Custom test suite class for sorting cases into suites automatically while globbing."""

    suite_flags = SuiteFlags.ALL

    def addTest(self, test: TestCase):
        if hasattr(test, "suite_flags") and isinstance(test.suite_flags, _SuiteFlags):
            self.suite_flags = test.suite_flags
        super().addTest(test)


def main() -> None:
    return UnitTest.main()
