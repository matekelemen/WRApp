""" @author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics
from KratosMultiphysics.python_solver import PythonSolver

# --- WRApp Imports ---
from .AsyncSolver import AsyncSolver

# --- STD Imports ---
import typing


## @addtogroup WRApplication
## @{
## @addtogroup AsyncAnalysis
## @{


class WrappedSolver(AsyncSolver):
    """ @brief Specialization of @ref AsyncSolver for wrapping a @ref PythonSolver.
        @classname WrappedSolver
        @details Default parameters:
                 @code
                 {
                    "type" : ""         // <== path of a PythonSolver available in the Registry
                    "parameters" : {}   // <== parameters forwarded to the solver's constructor
                 }
                 @endcode
    """

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        super().__init__(model, parameters)
        parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())
        wrapped_type: typing.Type[PythonSolver] = KratosMultiphysics.Registry[parameters["type"].GetString()]["type"]
        self.__wrapped_solver = wrapped_type(model, parameters)

        # This part of the initialization needs to happen before any calls
        # to Process::ExecuteInitialize, so it's added as an initial hook
        # before _Preprocess.
        #self.AddHook(MakeHook(self.__Initialize),
        #             SolutionStage.PRE_PREPROCESS)


    ## @name Properties
    ## @{


    @property
    def wrapped_solver(self) -> PythonSolver:
        return self.__wrapped_solver


    ## @}
    ## @name Static Members
    ## @{


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        """ @code
            {
                "type" : "",
                "parameters" : {}
            }
            @endcode
        """
        return KratosMultiphysics.Parameters(R"""{
            "type" : "",
            "parameters" : {}
        }""")


    ## @}
    ## @name Solution Flow
    ## @{


    def _Preprocess(self) -> None:
        self.__wrapped_solver.Initialize()


    def _Advance(self) -> None:
        while True:
            self.__wrapped_solver.AdvanceInTime(self.__wrapped_solver.GetComputingModelPart().ProcessInfo[KratosMultiphysics.TIME])
            self.__wrapped_solver.InitializeSolutionStep()
            self.__wrapped_solver.Predict()
            self._Synchronize()
            self.__wrapped_solver.FinalizeSolutionStep()
            if self.synchronization_predicate:
                break


    def _Synchronize(self) -> None:
        """ @brief Solves the current solution step once in the solver's current state."""
        converged = self.__wrapped_solver.SolveSolutionStep()
        if converged is not None or not converged:
            raise RuntimeError("Solver failed to converge")


    def _Postprocess(self) -> None:
        self.__wrapped_solver.Finalize()


    ## @}


    def __Initialize(self) -> None:
        self.__wrapped_solver.ImportModelPart()
        self.__wrapped_solver.PrepareModelPart()
        self.__wrapped_solver.AddDofs()


## @}