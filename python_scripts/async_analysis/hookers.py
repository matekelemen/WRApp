""" @author Máté Kelemen
    @brief 💃💃💃
    @details Don't get your hopes up, this module just provides some
             utility functions to help with assigning callable objects
             to the correct hook points of @ref AsyncSolver.
"""

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
from .AsyncSolver import AsyncSolver, SolutionStage

# --- STD Imports ---
import functools
import typing


def MakeHook(function: typing.Callable[[],typing.Any]) -> typing.Callable[[AsyncSolver],None]:
    """ @brief Transform a function taking no arguments into a hook, attachable to @ref AsyncSolver."""
    @functools.wraps(function)
    def wrapped(_: AsyncSolver) -> None:
        function()
    return wrapped


def AttachProcess(process: KratosMultiphysics.Process,
                  solver: AsyncSolver) -> None:
    solver.AddHook(MakeHook(process.ExecuteInitialize),
                   SolutionStage.PRE_PREPROCESS)
    solver.AddHook(MakeHook(process.ExecuteBeforeSolutionLoop),
                   SolutionStage.POST_PREPROCESS)
    solver.AddHook(MakeHook(process.ExecuteInitializeSolutionStep),
                   SolutionStage.PRE_ADVANCE)
    solver.AddHook(MakeHook(process.ExecuteFinalizeSolutionStep),
                   SolutionStage.POST_ADVANCE)
    solver.AddHook(MakeHook(process.ExecuteFinalize),
                   SolutionStage.PRE_POSTPROCESS)



