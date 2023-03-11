""" @author Máté Kelemen"""

__all__ = [
    "AsyncSolver"
]

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
from .SolutionStageScope import SolutionStageScope, AggregateSolutionStageScope
import KratosMultiphysics.WRApplication as WRApp

# --- STD Imports ---
import typing
import collections.abc
import io


## @addtogroup WRApplication
## @{
## @addtogroup AsyncAnalysis
## @{


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


    ## @name Public Members
    ## @{


    def Preprocess(self) -> "AsyncSolver.PreprocessScope":
        return self._preprocess_scope_type(self)


    def Advance(self) -> "AsyncSolver.AdvanceScope":
        return self._advance_scope_type(self)


    def Synchronize(self) -> "AsyncSolver.SynchronizeScope":
        return self._synchronize_scope_type(self)


    def Postprocess(self) -> "AsyncSolver.PostprocessScope":
        return self._postprocess_scope_type(self)


    def RunSolutionLoop(self) -> "AsyncSolver.SolutionLoopScope":
        return self._solution_loop_scope_type(self)


    def GetSolver(self, partition_name: str) -> "AsyncSolver":
        """ @brief Get the solver assigned to the specified partition."""
        return self.__solvers[partition_name]


    def WriteInfo(self, stream: io.StringIO, prefix: str = "") -> None:
        self.RunSolutionLoop().WriteInfo(stream, prefix)


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
        with AggregateSolutionStageScope([solver.Preprocess() for solver in self.__solvers.values()]) as preprocess:
            preprocess()


    def _Advance(self) -> None:
        """ @brief Keep solving steps until synchronization becomes necessary."""
        while True:
            with AggregateSolutionStageScope([solver.Advance() for solver in self.__solvers.values()]) as advance:
                advance()
            with AggregateSolutionStageScope([solver.Synchronize() for solver in self.__solvers.values()]) as synchronize:
                synchronize()
            if self.synchronization_predicate(self.model):
                break


    def _Synchronize(self) -> None:
        """ @brief Perform data synchronization and coupling tasks between partitions."""
        with AggregateSolutionStageScope([solver.Synchronize() for solver in self.__solvers.values()]) as synchronize:
            synchronize()


    def _TerminationPredicate(self) -> bool:
        """ @brief Predicate determining whether the solution loop should be terminated."""
        return all(subsolver._TerminationPredicate() for subsolver in self.__solvers.values())


    def _Postprocess(self) -> None:
        """ @brief Tasks to run if no more @ref AsyncSolver._Advance calls are made."""
        with AggregateSolutionStageScope([solver.Postprocess() for solver in self.__solvers.values()]) as postprocess:
            postprocess()


    def _RunSolutionLoop(self) -> None:
        while not self._TerminationPredicate():
            with self.Advance() as advance:
                advance()
            with self.Synchronize() as synchronize:
                synchronize()


    ## @}
    ## @name Solution Scope Types


    @property
    def _preprocess_scope_type(self) -> "typing.Type[AsyncSolver.PreprocessScope]":
        return AsyncSolver.PreprocessScope


    @property
    def _advance_scope_type(self) -> "typing.Type[AsyncSolver.AdvanceScope]":
        return AsyncSolver.AdvanceScope


    @property
    def _synchronize_scope_type(self) -> "typing.Type[AsyncSolver.SynchronizeScope]":
        return AsyncSolver.SynchronizeScope


    @property
    def _postprocess_scope_type(self) -> "typing.Type[AsyncSolver.PostprocessScope]":
        return AsyncSolver.PostprocessScope


    @property
    def _solution_loop_scope_type(self) -> "typing.Type[AsyncSolver.SolutionLoopScope]":
        return AsyncSolver.SolutionLoopScope


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


    ## @}
    ## @name Member Classes
    ## @{


    class SolverScope(SolutionStageScope):
        """ @brief Embed some part of @ref AsyncSolver in a @ref SolutionStageScope.
            @classname SolverScope
        """

        def __init__(self, solver: "AsyncSolver"):
            self.__solver = solver


        def WriteInfo(self, stream: io.StringIO, prefix: str = ""):
            stream.write(f"{prefix}Unknown scoped operation of solver '{type(self._solver).__name__}'\n")


        @property
        def _solver(self) -> "AsyncSolver":
            return self.__solver


        def _Preprocess(self) -> None:
            pass


        def _Postprocess(self) -> None:
            pass



    class PreprocessScope(SolverScope):
        """ @brief Embed @ref AsyncSolver._Preprocess in a @ref SolutionStageScope.
            @classname PreprocessScope
        """

        def __init__(self, solver: "AsyncSolver"):
            super().__init__(solver)


        def WriteInfo(self, stream: io.StringIO, prefix: str = ""):
            stream.write(f"{prefix}Preprocess solver '{type(self._solver).__name__}'\n")
            AggregateSolutionStageScope([self._solver.GetSolver(partition_name).Preprocess() for partition_name in self._solver.partitions]).WriteInfo(stream, prefix + "|  ")


        def __call__(self) -> None:
            self._solver._Preprocess()



    class AdvanceScope(SolverScope):
        """ @brief Embed @ref AsyncSolver._Advance in a @ref SolutionStageScope.
            @classname AdvanceScope
        """

        def __init__(self, solver: "AsyncSolver"):
            super().__init__(solver)


        def WriteInfo(self, stream: io.StringIO, prefix: str = ""):
            stream.write(f"{prefix}Advance solver '{type(self._solver).__name__}'\n")
            subprefix = prefix + "|  "
            stream.write(f"{subprefix}While not {type(self._solver).__name__}.synchronization_predicate:\n")
            AggregateSolutionStageScope([self._solver.GetSolver(partition_name).Advance() for partition_name in self._solver.partitions]).WriteInfo(stream, subprefix + "|  ")
            AggregateSolutionStageScope([self._solver.GetSolver(partition_name).Synchronize() for partition_name in self._solver.partitions]).WriteInfo(stream, subprefix + "|  ")


        def __call__(self) -> None:
            self._solver._Advance()



    class SynchronizeScope(SolverScope):
        """ @brief Embed @ref AsyncSolver._Synchronize in a @ref SolutionStageScope.
            @classname SynchronizeScope
        """

        def __init__(self, solver: "AsyncSolver"):
            super().__init__(solver)


        def WriteInfo(self, stream: io.StringIO, prefix: str = ""):
            stream.write(f"{prefix}Synchronize solver '{type(self._solver).__name__}'\n")
            AggregateSolutionStageScope([self._solver.GetSolver(partition_name).Synchronize() for partition_name in self._solver.partitions]).WriteInfo(stream, prefix + "|  ")


        def __call__(self) -> None:
            self._solver._Synchronize()



    class PostprocessScope(SolverScope):
        """ @brief Embed @ref AsyncSolver._Postprocess in a @ref SolutionStageScope.
            @classname PostprocessScope
        """

        def __init__(self, solver: "AsyncSolver"):
            super().__init__(solver)


        def WriteInfo(self, stream: io.StringIO, prefix: str = ""):
            stream.write(f"{prefix}Postprocess solver '{type(self._solver).__name__}'\n")
            AggregateSolutionStageScope([self._solver.GetSolver(partition_name).Postprocess() for partition_name in self._solver.partitions]).WriteInfo(stream, prefix + "|  ")


        def __call__(self) -> None:
            self._solver._Postprocess()


    class SolutionLoopScope(SolverScope):
        """ @brief Embed @ref AsyncSolver.Run in a @ref SolutionStageScope.
            @classname SolutionLoopScope
        """

        def __init__(self, solver: "AsyncSolver"):
            super().__init__(solver)


        def WriteInfo(self, stream: io.StringIO, prefix: str = ""):
            stream.write(f"{prefix}Run solution loop of solver '{type(self._solver).__name__}'\n")

            sub_prefix = prefix + "|  "
            self._solver.Preprocess().WriteInfo(stream, sub_prefix)
            stream.write(f"{sub_prefix}While not {type(self._solver).__name__}.termination_predicate\n")

            solution_loop_prefix = sub_prefix + "|  "
            self._solver.Advance().WriteInfo(stream, solution_loop_prefix)
            self._solver.Synchronize().WriteInfo(stream, solution_loop_prefix)

            self._solver.Postprocess().WriteInfo(stream, sub_prefix)


        def _Preprocess(self) -> None:
            with self._solver.Preprocess() as preprocess:
                preprocess()


        def __call__(self) -> None:
            self._solver._RunSolutionLoop()


        def _Postprocess(self) -> None:
            with self._solver.Postprocess() as postprocess:
                postprocess()


    ## @}


## @}
## @}
