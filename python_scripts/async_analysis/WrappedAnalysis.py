""" @author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics
from KratosMultiphysics.analysis_stage import AnalysisStage

# --- WRApp Imports ---
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
        analysis_type: typing.Type[AnalysisStage] = KratosMultiphysics.Registry[parameters["type"].GetString()]["type"]
        self.__wrapped = analysis_type(model, parameters["parameters"])
        self.__wrapped.Initialize()

        # Find the root model part
        root_model_part_name = self.__FindRootModelPartName(parameters["parameters"])
        if root_model_part_name is None:
            raise RuntimeError(f"Failed to find root model part name in {parameters['parameters']}")

        # Define the required parameters for the base class' constructor
        base_parameters = KratosMultiphysics.Parameters()
        base_parameters.AddValue("synchronization_predicate", parameters["synchronization_predicate"])
        super().__init__(model, base_parameters)


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


    ## @name Solution Flow
    ## @{


    def _Advance(self) -> None:
        while True:
            self.__wrapped.time = self.__wrapped._AdvanceTime()
            self.__wrapped.InitializeSolutionStep()
            self.__wrapped._GetSolver().Predict()
            converged = self.__wrapped._GetSolver().SolveSolutionStep()
            if converged is not None and not self.__wrapped._GetSolver().SolveSolutionStep():
                raise RuntimeError(f"{self.__wrapped._GetSolver()} failed to converge")
            self.__wrapped.FinalizeSolutionStep()
            self.__wrapped.OutputSolutionStep()
            if self.synchronization_predicate:
                break


    def _Synchronize(self) -> None:
        self.__wrapped._GetSolver().SolveSolutionStep()


    def _TerminationPredicate(self) -> bool:
        return not self.__wrapped.KeepAdvancingSolutionLoop()


    def _Postprocess(self) -> None:
        self.__wrapped.Finalize()


    ## @}


    def __FindRootModelPartName(self, parameters: KratosMultiphysics.Parameters) -> typing.Optional[str]:
        """ @brief Scan the input parameters for the analysis' root model part.
            @details Search for "model_part_name" in the following paths in order:
                     - root of the input parameters
                     - "solver_settings"
                     - "solver_settings" / "*solver_settings*"
        """
        output: typing.Optional[str] = None
        if parameters.Has("model_part_name"):
            output = parameters["model_part_name"].GetString() # <== fast-track this name
        elif parameters.Has("solver_settings"):
            subparameters = parameters["solver_settings"]
            if subparameters.Has("model_part_name"):
                return subparameters["model_part_name"].GetString() # <== fast-track this name
            else:
                for key, value in subparameters.items(): # <== multiple definitions forbidden from here on
                    if "solver_settings" in key:
                        if value.Has("model_part_name"):
                            if output is None:
                                output = value["model_part_name"].GetString()
                            elif output != value["model_part_name"].GetString():
                                raise RuntimeError(f"Failed to find unique root model part name in {parameters}")
        return output


## @}
## @}
