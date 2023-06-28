""" @author Máté Kelemen"""

__all__ = [
    "CoupledAsyncSolver"
]

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
from KratosMultiphysics import WRApplication as WRApp
from .SolutionStageScope import SolutionStageScope, AggregateSolutionStageScope
from .AsyncSolver import AsyncSolver

# --- STD Imports ---
import io
import typing


## @addtogroup WRApplication
## @{
## @addtogroup AsyncAnalysis
## @{


class CoupledAsyncSolver(AsyncSolver):
    """ @brief @ref AsyncSolver with coupling directives from @ref CoSimulationApplication.
        @classname CoupledAsyncSolver
        @details This class shoves most functionality from @ref CoSimulationCoupledSolver
                 into the interface set by @ref AsyncSolver.
    """

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        super().__init__(model, parameters)

        # Decide which DataCommunicator to use
        model_part_name = parameters["model_part_name"].GetString()
        self.__data_communicator: KratosMultiphysics.DataCommunicator
        if model_part_name:
            self.__data_communicator = model.GetModelPart(model_part_name).GetCommunicator().GetDataCommunicator()
        else:
            self.__data_communicator = KratosMultiphysics.ParallelEnvironment.GetDefaultDataCommunicator()

        self.__coupling_operation = WRApp.CoSimCoupling(
            self,
            model,
            self.__data_communicator,
            self.parameters["coupling"])


    ## @name Solution Flow
    ## @{


    def _Synchronize(self) -> None:
        with self.__coupling_operation as couple:
            with AggregateSolutionStageScope([self.GetSolver(partition_name).Synchronize() for partition_name in self.partitions]) as subsync:
                subsync()
            couple()


    ## @}
    ## @name Solution Scope Types
    ## @{


    @property
    def _synchronize_scope_type(self) -> "typing.Type[AsyncSolver.SynchronizeScope]":
        return CoupledAsyncSolver.SynchronizeScope


    ## @}
    ## @name Properties
    ## @{


    @property
    def _coupling_operation(self) -> SolutionStageScope:
        return self.__coupling_operation


    ## @}
    ## @name Static Members
    ## @{


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        """ @brief Uninitialized parameters for validation.
            @details @a "model_part_name" is optional, and is used for identifying
                     the @ref ModelPart whose @ref DataCommunicator will be used for
                     MPI calls. If left blank, the default data communicator is used.
            @details Default parameters:
                     @code
                     {
                         ...,
                         "model_part_name" : "",
                         "coupling" : {
                             "interface_datasets" : []
                             "transform_operators" : {},
                             "coupling_sequence" : [],
                             "convergence_accelerators" : [],
                             "convergence_criteria" : [],
                             "max_iterations" : 0
                             "verbosity" : 2
                         },
                         "predictors" : []
                     }
                     @endcode
        """
        output = super().GetDefaultParameters()
        output.AddString("model_part_name", "")
        output.AddValue("coupling", WRApp.CoSimCoupling.GetDefaultParameters())
        return output


    ## @}
    ## @name Member Classes
    ## @{


    class SynchronizeScope(AsyncSolver.SynchronizeScope):

        def __init__(self, solver: "CoupledAsyncSolver"):
            super().__init__(solver)


        def WriteInfo(self, stream: io.StringIO, prefix: str = ""):
            #super().WriteInfo(stream, prefix)
            subprefix = prefix + "|  "
            AggregateSolutionStageScope([
                self._solver.GetSolver(partition_name).Synchronize() for partition_name in self._solver.partitions
            ]).WriteInfo(stream, subprefix)
            self._solver._coupling_operation.WriteInfo(stream, subprefix)


    ## @}


## @}
## @}
