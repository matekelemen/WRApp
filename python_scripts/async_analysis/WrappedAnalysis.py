""" @author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics
from KratosMultiphysics.analysis_stage import AnalysisStage

# --- WRApp Imports ---
from .AsyncSolver import AsyncSolver

# --- STD Imports ---
import typing
import io


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
        analysis_type: typing.Type[AnalysisStage] = KratosMultiphysics.Registry[parameters["type"].GetString()]["type"]
        self.__wrapped = analysis_type(model, parameters["parameters"])
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
            if self._is_open:
                self.__wrapped.FinalizeSolutionStep()
                self.__wrapped.OutputSolutionStep()
            self.__wrapped.time = self.__wrapped._AdvanceTime()
            #with self.Synchronize() as synchronize:
            #    synchronize()
            self.__wrapped.InitializeSolutionStep()
            self.__wrapped._GetSolver().Predict()
            self._is_open = True
            if self.synchronization_predicate(self.model):
                break
            if self._is_open:
                self.__wrapped.FinalizeSolutionStep()
                self.__wrapped.OutputSolutionStep()
                self._is_open = False


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


        def WriteInfo(self, stream: io.StringIO, prefix: str = "") -> None:
            stream.write(f"{prefix}{type(self._solver._GetWrapped()).__name__}.InitializeSolutionStep\n")
            stream.write(f"{prefix}{type(self._solver._GetWrapped()._GetSolver()).__name__}.Predict\n")
            stream.write(f"{prefix}{type(self._solver._GetWrapped()._GetSolver()).__name__}.SolveSolutionStep\n")
            stream.write(f"{prefix}{type(self._solver._GetWrapped()).__name__}.FinalizeSolutionStep\n")


        def _Preprocess(self) -> None:
            #if not self._solver._is_open:
            #    self._solver._is_open = True
            #    self._solver._GetWrapped().InitializeSolutionStep()
            #    self._solver._GetWrapped()._GetSolver().Predict()
            pass


        def _Postprocess(self) -> None:
            #if self._solver._is_open:
            #    self._solver._GetWrapped().FinalizeSolutionStep()
            #    self._solver._GetWrapped().OutputSolutionStep()
            #    self._solver._is_open = False
            pass


    ## @}


    #def __FindRootModelPartName(self, parameters: KratosMultiphysics.Parameters) -> typing.Optional[str]:
    #    """ @brief Scan the input parameters for the analysis' root model part.
    #        @details Search for "model_part_name" in the following paths in order:
    #                 - root of the input parameters
    #                 - "solver_settings"
    #                 - "solver_settings" / "*solver_settings*"
    #    """
    #    output: typing.Optional[str] = None
    #    if parameters.Has("model_part_name"):
    #        output = parameters["model_part_name"].GetString() # <== fast-track this name
    #    elif parameters.Has("solver_settings"):
    #        subparameters = parameters["solver_settings"]
    #        if subparameters.Has("model_part_name"):
    #            return subparameters["model_part_name"].GetString() # <== fast-track this name
    #        else:
    #            for key, value in subparameters.items(): # <== multiple definitions forbidden from here on
    #                if "solver_settings" in key:
    #                    if value.Has("model_part_name"):
    #                        if output is None:
    #                            output = value["model_part_name"].GetString()
    #                        elif output != value["model_part_name"].GetString():
    #                            raise RuntimeError(f"Failed to find unique root model part name in {parameters}")
    #    return output


## @}
## @}
