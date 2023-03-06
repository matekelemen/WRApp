""" @author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics
from KratosMultiphysics.python_solver import PythonSolver

# --- WRApp Imports ---
from .AsyncSolver import AsyncSolver, SolutionStage
from .hookers import MakeHook

# --- STD Imports ---
import typing


class WrappedSolver(AsyncSolver):
    """ @brief Specialization of @ref AsyncSolver for wrapping a @ref PythonSolver.
        @classname WrappedSolver
    """

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        super().__init__(model, parameters)
        wrapped_type: typing.Type[PythonSolver] = KratosMultiphysics.Registry[parameters["type"].GetString()]["type"]
        self.__wrapped_solver = wrapped_type(model, parameters)

        # This part of the initialization needs to happen before any calls
        # to Process::ExecuteInitialize, so it's added as an initial hook
        # before _Preprocess.
        self.AddHook(MakeHook(self.__Initialize),
                     SolutionStage.PRE_PREPROCESS)

    def _Preprocess(self) -> None:
        self.__wrapped_solver.Initialize()


    def _Advance(self) -> None:
        while not self.synchronization_predicate(self):
            self.__wrapped_solver.AdvanceInTime(self.__wrapped_solver.GetComputingModelPart().ProcessInfo[KratosMultiphysics.TIME])
            self.__wrapped_solver.InitializeSolutionStep()
            self.__wrapped_solver.Predict()
            converged = self.__wrapped_solver.SolveSolutionStep()
            if converged is not None or not converged:
                raise RuntimeError("Solver failed to converge")
            self.__wrapped_solver.FinalizeSolutionStep()


    def _Postprocess(self) -> None:
        self.__wrapped_solver.Finalize()


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        """ @code
            {
                ...,
                "type" : "",
                "parameters" : {}
            }
            @endcode
        """
        output = super().GetDefaultParameters()
        output.AddString("type", "")
        output.AddValue("parameters", KratosMultiphysics.Parameters())
        return output


    def __Initialize(self) -> None:
        self.__wrapped_solver.ImportModelPart()
        self.__wrapped_solver.PrepareModelPart()
        self.__wrapped_solver.AddDofs()
