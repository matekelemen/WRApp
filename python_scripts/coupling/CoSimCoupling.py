""" @author Máté Kelemen"""

__all__ = [
    "CoSimCoupling"
]

# --- Core Imports ---
import KratosMultiphysics

# --- CoSim Imports ---
from KratosMultiphysics.CoSimulationApplication.factories.helpers import CreateDataTransferOperators
from KratosMultiphysics.CoSimulationApplication.base_classes.co_simulation_data_transfer_operator import CoSimulationDataTransferOperator
from KratosMultiphysics.CoSimulationApplication.coupling_interface_data import CouplingInterfaceData
from KratosMultiphysics.CoSimulationApplication.convergence_criteria.convergence_criteria_wrapper import ConvergenceCriteriaWrapper

# --- WRApp Imports ---
from ..async_analysis.SolutionStageScope import SolutionStageScope
from ..async_analysis.AsyncSolver import AsyncSolver
import KratosMultiphysics.WRApplication as WRApp

# --- STD Imports ---
import io
import typing
import contextlib


## @addtogroup WRApplication
## @{
## @addtogroup AsyncAnalysis
## @{


class SubSynchronization(WRApp.WRAppClass, KratosMultiphysics.Operation):
    """ @brief A class wrapping @ref AsnycSolver._Synchronize in a @ref KratosMultiphysics.Operation.
        @classname SubSynchronization
        @details This operation is meant to be executed as part of the coupling sequence of
                 @ref CoSimCoupling, in between calls to @ref DatasetTransfer operations.
        @details Default parameters:
                 @code
                 {
                    "partition" : "" // <== partition to synchronize
                 }
                 @endcode
    """

    def __init__(self,
                 solver: AsyncSolver,
                 parameters: KratosMultiphysics.Parameters):
        WRApp.WRAppClass.__init__(self)
        KratosMultiphysics.Operation.__init__(self)
        parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())
        self.__solver = solver.GetSolver(parameters["partition"].GetString())


    def Execute(self) -> None:
        with self.__solver.Synchronize() as synchronize:
            synchronize()


    @classmethod
    def Factory(cls,
                solver: "WRApp.AsyncSolver",
                parameters: KratosMultiphysics.Parameters) -> "SubSynchronization":
        return SubSynchronization(solver, parameters)


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters(R"""{
            "partition" : ""    // <== name of the partition to synchronize
        }""")



class CoSimCoupling(SolutionStageScope, WRApp.WRAppClass):
    """ @brief Wrapper for CoSimulationApplication coupling procedures.
        @classname CoSimCoupling
        @details Default parameters:
                 @code
                 {
                    "interface_datasets" : [],
                    "transform_operators" : {},
                    "coupling_sequence" : [],
                    "convergence_accelerators" : [],
                    "convergence_criteria" : [],
                    "max_iterations" : 0
                    "verbosity" : 2
                 }
                 @endcode
                 @a "transform_operators" is forwarded to @ref CoSimulationApplication.factories.helpers.CreateDataTransferOperators.
                 @a "coupling_operations" is forwarded to CoSimulationApplication.factories.helpers.CreateCouplingOperations.
        @details Items in @a "interface_datasets" represent exposed sets of data on partition interfaces. The expected format
                 of each item:
                 @code
                 {
                    "name" : "",            // <== name of the dataset
                    "partition" : "",       // <== name of related partition
                    "model_part_name" : "", // <== name of the ModelPart within the partition the dataset is defined on
                    "dimension" : 0,        // <== number of components in each item of the dataset
                    "variable_name" : ""    // <== name of the variable the dataset refers to
                 }
                 @endcode
        @details Each item in @a "coupling_sequence" either defines a fetch-transform-write operation @ref DatasetTransfer
                 or a subsynchronization (usually a single call to @ref PythonSolver.SolveSolutionStep) @ref SubSynchronization.
                 Each item is expected in the following format:
                 @code
                 {
                    "type" : "",        // <== "trasfer" or "subsync"
                    "parameters" : {}   // <== parameters passed on to the appropriate constructor
                 }
                 @endcode
                 - fetch a specific dataset from a source partition
                 - transform the fetched dataset
                 - write the transformed dataset to a dataset defined in the target partition
    """

    def __init__(self,
                 solver: AsyncSolver,
                 parameters: KratosMultiphysics.Parameters):
        WRApp.WRAppClass.__init__(self)
        parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())
        self.__solver_root = solver
        self.__parameters = parameters

        self.__max_iterations = parameters["max_iterations"].GetInt()
        self.__verbosity = parameters["verbosity"].GetInt()

        # Coupling subiteration utilities
        self.__convergence_criteria = [WRApp.ConvergenceCriterion(solver.model, criterion_parameters) for criterion_parameters in parameters["convergence_criteria"].values()]

        self.__convergence_accelerators = [WRApp.ConvergenceAccelerator(solver.model, accelerator_parameters) for accelerator_parameters in parameters["convergence_accelerators"].values()]
        self.__accelerator_scopes: "typing.Optional[list[WRApp.ConvergenceAccelerator.AcceleratorScope]]" = None

        # Create a list of operations that must be executed in order at each synchronization
        self.__coupling_sequence = self.__MakeCouplingSequence(self.parameters["coupling_sequence"])


    def _Preprocess(self) -> None:
        self.__accelerator_scopes = [accelerator.__enter__() for accelerator in self.__convergence_accelerators]


    def __call__(self) -> None:
        """ @brief Execute all items in the coupling sequence in the order they were defined."""
        with contextlib.ExitStack() as scope_stack:
            criterion_scopes = [scope_stack.enter_context(scope) for scope in self.__convergence_criteria]
            nonlinear_accelerator_scopes = [scope_stack.enter_context(scope) for scope in self.__accelerator_scopes]
            for i_couple in range(self.__max_iterations):
                # Coupling subiter utils preproc
                for scope in nonlinear_accelerator_scopes:
                    scope.AddTerm()

                for criterion in criterion_scopes:
                    criterion.AddTerm()

                # Perform coupling operations in the defined order, consisting of
                # - data transfer between partitions
                # - partition synchronization
                for operation in self.__coupling_sequence:
                    operation.Execute()

                # Exit early if all convergence criteria are satisfied
                if all(criterion.HasConverged() for criterion in criterion_scopes):
                    if self.__verbosity:
                        print(f"Coupling converged after {i_couple + 1} iteration{'s' if 1 < i_couple else ''}")
                    return

                if i_couple + 1 < self.__max_iterations:
                    for scope in nonlinear_accelerator_scopes:
                        scope.Relax()

        # If the flow reached this point, the coupling failed
        raise RuntimeError(f"Coupling failed to converge in {self.__max_iterations} iteration{'s' if 1 < self.__max_iterations else ' '}")


    def _Postprocess(self) -> None:
        for scope in self.__convergence_accelerators:
            scope.__exit__(None, None, None)


    ## @name Properties
    ## @{


    @property
    def parameters(self) -> KratosMultiphysics.Parameters:
        return self.__parameters


    ## @}
    ## @name Static Members
    ## @{


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters(R"""{
            "coupling_sequence" : [],
            "convergence_accelerators" : [],
            "convergence_criteria" : [],
            "max_iterations" : 0,
            "verbosity" : 0
        }""")


    def __MakeCouplingSequence(self, parameters: KratosMultiphysics.Parameters) -> "list[KratosMultiphysics.Operation]":
        """ @brief Construct a list of objects responsible for data fetching, transform, and writing between partitions.
            @details The input @a parameters is expected as a list of objects in the following format:
                     @code
                     {
                        "type" : "",        // <== defines a DatasetTransform or a SubSynchronization
                        "parameters" : {}   // <== parameters passed on to DatasetTransfer or SubSynchronization
                     }
                     @endcode
                     Each item represents either a @ref DatasetTransfer or a @ref SubSynchronization.
        """
        output: "list[KratosMultiphysics.Operation]" = []
        for item in parameters.values():
            output.append(WRApp.GetRegisteredClass(item["type"].GetString()).Factory(
                self.__solver_root,
                item["parameters"]))
        return output


    ## @}


## @}
## @}
