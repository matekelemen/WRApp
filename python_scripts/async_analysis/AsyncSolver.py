""" @author Máté Kelemen"""

__all__ = [
    "AsyncSolver"
]

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
from .SynchronizationPredicate import SynchronizationPredicate
import KratosMultiphysics.WRApplication as WRApp

# --- STD Imports ---
import typing
import enum
import collections.abc


## @addtogroup WRApplication
## @{
## @addtogroup AsyncAnalysis
## @{


class SolutionStage(enum.Enum):
    """ @brief Enum for identifying solver stages to hook to.
        @classname SolutionStage
    """
    PRE_PREPROCESS   = 0
    POST_PREPROCESS  = 1
    PRE_ADVANCE      = 2
    PRE_SYNCHRONIZE  = 3
    POST_SYNCHRONIZE = 4
    POST_ADVANCE     = 5
    PRE_POSTPROCESS  = 6
    POST_POSTPROCESS = 7


class AsyncSolver(WRApp.WRAppClass):
    """ @brief Base class for composable solvers that handle their domains asynchronously.
        @classname AsyncSolver
        @details Default parameters:
                 @code
                 {
                     "model_part_name" : "",
                     "partitions" : {},
                     "synchronization_predicate" : {
                         "type" : "",
                         "parameters" : {}
                     }
                 }
                 @endcode
                 Each partition has a solver (@ref AsyncSolver) and a predicate for determining
                 when the partition requires synchronization (@ref SynchronizationPredicate),
                 both of which must be present in the @ref Registry.
                 Partition configuration is expected in the following format:
                 @code
                 {
                    "type" : "",
                    "parameters" : {}
                 }
                 @endcode
    """

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        super().__init__()
        parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())
        self.__model_part = model.GetModelPart(parameters["model_part_name"].GetString())
        self.__parameters = parameters

        # A dict mapping partition names to solvers
        self.__solvers: "dict[str,AsyncSolver]" = {}

        # A dict mapping partition names to synchronization predicates
        predicate_type: typing.Type[SynchronizationPredicate] = KratosMultiphysics.Registry[self.__parameters["synchronization_predicate"]["type"].GetString()]["type"]
        self.__synchronization_predicate = predicate_type(self.__parameters["synchronization_predicate"]["parameters"])

        for partition_name, partition_parameters in self.__parameters["partitions"].items():
            solver_type: typing.Type[AsyncSolver] = KratosMultiphysics.Registry[partition_parameters["type"].GetString()]["type"]
            self.__solvers[partition_name] = solver_type(model, partition_parameters["parameters"])

        # Initialize empty hooks
        self.__hooks: "dict[SolutionStage,list[typing.Callable[[AsyncSolver],None]]]" = dict((stage, []) for stage in SolutionStage)


    ## @name Public Members
    ## @{


    def RunSolutionLoop(self) -> None:
        while not self._TerminationPredicate():
            self.__Advance()
            self.__Synchronize()


    def Run(self) -> None:
        self.__Preprocess()
        self.RunSolutionLoop()
        self.__Postprocess()


    def GetSolver(self, partition_name: str) -> "AsyncSolver":
        """ @brief Get the solver assigned to the specified partition."""
        return self.__solvers[partition_name]


    def AddHook(self,
                hook: typing.Callable[["AsyncSolver"],None],
                stage: SolutionStage) -> None:
        """ @brief Append the list of hooks for the specified stage."""
        self.__hooks[stage].append(hook)


    ## @}
    ## @name Properties
    ## @{


    @property
    def model_part(self) -> KratosMultiphysics.ModelPart:
        return self.__model_part


    @property
    def partitions(self) -> collections.abc.KeysView[str]:
        return self.__solvers.keys()


    @property
    def parameters(self) -> KratosMultiphysics.Parameters:
        return self.__parameters


    @property
    def synchronization_predicate(self) -> SynchronizationPredicate:
        return self.__synchronization_predicate


    ## @}
    ## @name Static Members
    ## @{


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        """ @code
            {
                "model_part_name" : "",
                "partitions" : {},
                "synchronization_predicate" : {
                    "type" : "",
                    "parameters" : {}
                }
            }
            @endcode
        """
        return KratosMultiphysics.Parameters(R"""{
            "model_part_name" : "",
            "partitions" : {},
            "synchronization_predicate" : {
                "type" : "",
                "parameters" : {}
            }
        }""")


    ## @}
    ## @name Protected Members
    ## @{


    def _Preprocess(self) -> None:
        """ @brief Tasks to run before any calls to @ref AsyncSolver._Advance."""
        for solver in self.__solvers.values():
            solver._Preprocess()


    def _Advance(self) -> None:
        """ @brief Keep solving steps until synchronization becomes necessary."""
        while not self.__synchronization_predicate(self):
            for solver in self.__solvers.values():
                solver._Advance()
            for solver in self.__solvers.values():
                solver._Synchronize()


    def _Synchronize(self) -> None:
        """ @brief Perform data synchronization and coupling tasks between partitions."""
        pass


    def _TerminationPredicate(self) -> bool:
        """ @brief Predicate determining whether the solution loop should be terminated."""
        return True


    def _Postprocess(self) -> None:
        """ @brief Tasks to run if no more @ref AsyncSolver._Advance calls are made."""
        for solver in self.__solvers.values():
            solver._Postprocess()


    ## @}
    ## @name Private Members
    ## @}


    def __InvokeHooks(self, stage: SolutionStage) -> None:
        for hook in self.__hooks[stage]:
            hook(self)


    def __Preprocess(self) -> None:
        """ @brief Sandwich @ref AsyncSolver._Preprocess between hook calls."""
        self.__InvokeHooks(SolutionStage.PRE_PREPROCESS)
        self._Preprocess()
        self.__InvokeHooks(SolutionStage.POST_POSTPROCESS)


    def __Advance(self) -> None:
        """ @brief Sandwich @ref AsyncSolver._Advance between hook calls."""
        self.__InvokeHooks(SolutionStage.PRE_ADVANCE)
        self._Advance()
        self.__InvokeHooks(SolutionStage.POST_ADVANCE)


    def __Synchronize(self) -> None:
        """ @brief Sandwich @ref AsyncSolver._Synchronize between hook calls."""
        self.__InvokeHooks(SolutionStage.PRE_SYNCHRONIZE)
        self._Synchronize()
        self.__InvokeHooks(SolutionStage.POST_SYNCHRONIZE)


    def __Postprocess(self) -> None:
        """ @brief Sandwich @ref AsyncSolver._Postprocess between hook calls."""
        self.__InvokeHooks(SolutionStage.PRE_POSTPROCESS)
        self._Postprocess()
        self.__InvokeHooks(SolutionStage.POST_POSTPROCESS)


    ## @}


## @}
## @}
