""" @author Máté Kelemen"""

__all__ = [
    "SynchronizationPredicate"
]

# --- Core Imports ---
from KratosMultiphysics.python_solver import PythonSolver

# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp

# --- STD Imports ---
import abc


class SynchronizationPredicate(WRApp.WRAppClass):
    """ @brief Predicate taking a @ref PythonSolver and deciding whether it needs synchronization with its coupled solvers based on its current state."""

    def __init__(self, *_):
        super().__init__()


    @abc.abstractmethod
    def __call__(self, solver: PythonSolver) -> bool:
        """ @brief Check whether the provided solver requires synchronization with its coupled solvers based on its current state."""
        pass
