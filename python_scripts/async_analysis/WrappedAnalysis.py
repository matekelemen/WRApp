""" @author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics
from KratosMultiphysics.analysis_stage import AnalysisStage

# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp
from .AsyncSolver import AsyncSolver

# --- STD Imports ---
import typing


## @addtogroup WRApplication
## @{
## @addtogroup AsyncAnalysis
## @{


class WrappedAnalysis(AsyncSolver):
    """ @brief Integrate a @ref KratosMultiphysics.AnalysisStage into @ref AsyncSolver._Synchronize.
        @classname WrappedAnalysis
        @details Default Parameters:
                 @code
                 {
                    "type" : "",        // <== AnalysisStage type available from the Registry
                    "parameters" : {},  // <== parameters passed on to the constructor
                    "synchronization_predicate" : {
                         "type" : "",
                         "parameters" : {}
                     }
                 }
                 @endcode
    """

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        # First, construct the analysis to load required data
        # and create the model tree.
        parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())
        self.__wrapped: AnalysisStage = WRApp.RegisteredClassFactory(parameters["type"].GetString(),
                                                                     model,
                                                                     parameters["parameters"])
        self.__wrapped.Initialize()

        # Define the required parameters for the base class' constructor
        base_parameters = KratosMultiphysics.Parameters()
        base_parameters.AddValue("synchronization_predicate", parameters["synchronization_predicate"])
        super().__init__(model, base_parameters)
        self._is_open = False


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        output = super().GetDefaultParameters()
        output.RecursivelyAddMissingParameters(KratosMultiphysics.Parameters(R"""{
            "type" : "",
            "parameters" : {},
            "synchronization_predicate" : {
                "type" : "",
                "parameters" : {}
            }
        }"""))
        return output


    def _GetWrapped(self) -> AnalysisStage:
        return self.__wrapped


    ## @name Solution Flow
    ## @{


    def _Advance(self) -> None:
        while True:
            self._Close()
            self.__wrapped.time = self.__wrapped._AdvanceTime()
            self._Open()
            self.__wrapped._GetSolver().SolveSolutionStep()
            if self.synchronization_predicate(self.model):
                break
            self._Close(output = True)


    def _Synchronize(self) -> None:
        converged = self.__wrapped._GetSolver().SolveSolutionStep()
        #if converged is not None and not converged:
        #    raise RuntimeError(f"{self.__wrapped._GetSolver()} failed to converge")


    def _TerminationPredicate(self) -> bool:
        return not self.__wrapped.KeepAdvancingSolutionLoop()


    def _Postprocess(self) -> None:
        self.__wrapped.Finalize()


    ## @}
    ## @name Solution Scope Types
    ## @{


    @property
    def _synchronize_scope_type(self) -> "typing.Type[AsyncSolver.SynchronizeScope]":
        return WrappedAnalysis.SynchronizeScope


    ## @}
    ## @name Member Classses
    ## @{


    class SynchronizeScope(AsyncSolver.SynchronizeScope):
        """ @brief Sandwich @ref AnalysisStage.SolveSolutionStage between "initialization" and "finalization".
            @classname SynchronizeScope
        """

        def __init__(self, solver: "WrappedAnalysis"):
            super().__init__(solver)


        def _Preprocess(self) -> None:
            self._solver._Open()
            pass


        def _Postprocess(self) -> None:
            #self._solver._Close(output = True)
            pass


    ## @}


    def _Open(self) -> None:
        if not self._is_open:
            self.__wrapped.InitializeSolutionStep()
            self.__wrapped._GetSolver().Predict()
            self._is_open = True


    def _Close(self, output = False) -> None:
        if self._is_open:
            self.__wrapped.FinalizeSolutionStep()
            if output:
                self.__wrapped.OutputSolutionStep()
            self._is_open = False


## @}
## @}
