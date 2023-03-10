""" @author Máté Kelemen"""

__all__ = [
    "AsyncSolver",
    "SolutionStage"
]

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp

# --- STD Imports ---
import abc
import typing
import enum
import collections.abc
#import io


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
                     "partitions" : [],
                     "synchronization_predicate" : {
                         "type" : "WRApplication.ConstModelPredicate",
                         "parameters" : [{"value" : true}]
                     }
                 }
                 @endcode
                 Each partition has a solver (@ref AsyncSolver) and a predicate for determining
                 when the partition requires synchronization (@ref ModelPredicate ),
                 both of which must be present in the @ref Registry.
                 Partition configuration is expected in the following format:
                 @code
                 {
                    "name" : "",        // <== partition name
                    "type" : "",        // <== solver path in registry
                    "parameters" : {}   // <== subparameters passed on to the solver's constructor
                 }
                 @endcode
        @details @a "termination_predicate"
    """

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        super().__init__()
        parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())
        self.__model = model
        self.__parameters = parameters

        # A dict mapping partition names to solvers
        self.__solvers: "dict[str,AsyncSolver]" = self.__MakePartitions(model, self.parameters["partitions"])

        # A dict mapping partition names to synchronization predicates
        predicate_type: typing.Type[WRApp.ModelPredicate] = KratosMultiphysics.Registry[self.__parameters["synchronization_predicate"]["type"].GetString()]["type"]
        self.__synchronization_predicate = predicate_type(self.__parameters["synchronization_predicate"]["parameters"])

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


    #def GetInfo(self, stream: io.StringIO, prefix: str = "") -> None:
    #    for hook in self.__hooks[SolutionStage.PRE_PREPROCESS]:
    #        stream.write(f"{prefix}Run {hook}\n")
    #    for partition_name, solver in self.__solvers.items():
    #        stream.write(f"{prefix}Preprocess on partition '{}'")


    ## @}
    ## @name Properties
    ## @{


    @property
    def model(self) -> KratosMultiphysics.Model:
        return self.__model


    @property
    def partitions(self) -> "collections.abc.KeysView[str]":
        return self.__solvers.keys()


    @property
    def parameters(self) -> KratosMultiphysics.Parameters:
        return self.__parameters


    @property
    def synchronization_predicate(self) -> WRApp.ModelPredicate:
        return self.__synchronization_predicate


    ## @}
    ## @name Static Members
    ## @{


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        """ @code
            {
                "partitions" : [],
                "synchronization_predicate" : {
                    "type" : "WRApplication.ConstModelPredicate",
                    "parameters" : [{"value" : true}]
                }
            }
            @endcode
        """
        return KratosMultiphysics.Parameters(R"""{
            "partitions" : [],
            "synchronization_predicate" : {
                "type" : "WRApplication.ConstModelPredicate",
                "parameters" : [{"value" : true}]
            }
        }""")


    ## @}
    ## @name Solution Flow
    ## @{


    def _Preprocess(self) -> None:
        """ @brief Tasks to run before any calls to @ref AsyncSolver._Advance."""
        for solver in self.__solvers.values():
            solver._Preprocess()


    def _Advance(self) -> None:
        """ @brief Keep solving steps until synchronization becomes necessary."""
        while True:
            for solver in self.__solvers.values():
                solver._Advance()
            for solver in self.__solvers.values():
                solver._Synchronize()
            if self.synchronization_predicate:
                break


    def _Synchronize(self) -> None:
        """ @brief Perform data synchronization and coupling tasks between partitions."""
        pass


    def _TerminationPredicate(self) -> bool:
        """ @brief Predicate determining whether the solution loop should be terminated."""
        return all(subsolver._TerminationPredicate() for subsolver in self.__solvers.values())


    def _Postprocess(self) -> None:
        """ @brief Tasks to run if no more @ref AsyncSolver._Advance calls are made."""
        for solver in self.__solvers.values():
            solver._Postprocess()


    ## @}
    ## @name Private Members
    ## @{


    def __MakePartitions(self,
                         model: KratosMultiphysics.Model,
                         parameters: KratosMultiphysics.Parameters) -> "dict[str,AsyncSolver]":
        """ @brief Construct subsolvers.
            @returns A dict mapping partition names to solvers.
        """
        output: "dict[str,AsyncSolver]" = {}
        default_solver_parameters = KratosMultiphysics.Parameters(R"""{
            "name" : "",
            "type" : "",
            "parameters" : {}
        }""")

        # Construct subsolvers
        for solver_parameters in parameters.values():
            solver_parameters.ValidateAndAssignDefaults(default_solver_parameters)
            partition_name = solver_parameters["name"].GetString()
            solver_type: typing.Type[AsyncSolver] = KratosMultiphysics.Registry[solver_parameters["type"].GetString()]["type"]

            # The specified solver type must be derived from AsyncSolver
            if not issubclass(solver_type, AsyncSolver):
                raise TypeError(f"Expecting an AsyncSolver, but got {solver_type} in {solver_parameters}")

            # No duplicate partition names allowed
            if partition_name in output:
                raise NameError(f"Duplicate partition name '{partition_name}' in {solver_parameters}")

            output[partition_name] = solver_type(model, solver_parameters["parameters"])
        return output


    def __InvokeHooks(self, stage: SolutionStage) -> None:
        for hook in self.__hooks[stage]:
            hook(self)


    def __Preprocess(self) -> None:
        """ @brief Sandwich @ref AsyncSolver._Preprocess between hook calls."""
        self.__InvokeHooks(SolutionStage.PRE_PREPROCESS)
        self._Preprocess()
        self.__InvokeHooks(SolutionStage.POST_PREPROCESS)


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
