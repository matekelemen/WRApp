""" @author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp

# --- STD Imports ---
import typing


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
                    "partitions" : {}
                 }
                 @endcode
                 Each partition has a solver (@ref AsyncSolver) and a predicate for determining
                 when the partition requires synchronization (@ref SynchronizationPredicate),
                 both of which must be present in the @ref Registry.
                 Partition configuration is expected in the following format:
                 @code
                 {
                    "solver" : {
                        "type" : "",
                        "parameters" : {}
                    },
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
        super().__init__()
        self.__model = model
        self.__parameters = parameters
        self.__parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())

        # A dict mapping partition names to solvers
        self.__solvers: "dict[str,AsyncSolver]" = {}

        # A dict mapping partition names to synchronization predicates
        self.__synchronization_predicates: "dict[str,WRApp.SynchronizationPredicate]" = {}

        for partition_name, partition_parameters in self.__parameters["partitions"].items():
            solver_parameters = partition_parameters["solver"]
            solver_type: typing.Type[AsyncSolver] = KratosMultiphysics.Registry[solver_parameters["type"].GetString()]
            self.__solvers[partition_name] = solver_type(model, solver_parameters["parameters"])

            synchronization_predicate_parameters = partition_parameters["synchronization_predicate"]
            predicate_type: typing.Type[WRApp.SynchronizationPredicate] = KratosMultiphysics.Registry[synchronization_predicate_parameters["type"].GetString()]
            self.__synchronization_predicates[partition_name] = predicate_type(synchronization_predicate_parameters["parameters"])


    def Preprocess(self) -> None:
        """ @brief Tasks to run before any calls to @ref AsyncSolver.AdvancePartition."""
        pass


    def AdvancePartition(self,
                         solver: "AsyncSolver",
                         predicate: WRApp.SynchronizationPredicate) -> None:
        """ @brief Keep solving steps until synchronization becomes necessary.
            @param solver: @ref AsyncSolver responsible only for its own partition.
            @param predicate: a functor that checks the state of a @ref AsyncSolver and decides
                              whether synchronization/coupling is necessary with other solvers.
                              This functor is invoked <b>before</b> each solution step.
        """
        solver.AdvancePartition(solver, predicate)


    def Synchronize(self) -> None:
        pass


    def TerminationPredicate(self) -> bool:
        return True


    def Postprocess(self) -> None:
        """ @brief Tasks to run if no more @ref AsyncSolver.AdvancePartition calls are made."""
        pass


    def RunSolutionLoop(self) -> None:
        while not self.TerminationPredicate():
            all(self.AdvancePartition(solver, predicate)
                    for solver, predicate
                        in zip(self.__solvers.values(), self.__synchronization_predicates.values()))
            self.Synchronize()


    def Run(self) -> None:
        self.Preprocess()
        self.RunSolutionLoop()
        self.Postprocess()


    def GetSolver(self, partition_name: str) -> "AsyncSolver":
        return self.__solvers[partition_name]


    def GetSynchronizationPredicate(self, partition_name: str) -> WRApp.SynchronizationPredicate:
        return self.__synchronization_predicates[partition_name]


    @property
    def model(self) -> KratosMultiphysics.Model:
        return self.__model


    @property
    def parameters(self) -> KratosMultiphysics.Parameters:
        return self.__parameters


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        """ @code
            {
                "partitions" : {}
            }
            @endcode
        """
        return KratosMultiphysics.Parameters(R"""{
            "partitions" : {}
        }""")


## @}
## @}
