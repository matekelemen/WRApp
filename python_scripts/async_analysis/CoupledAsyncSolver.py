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
        self.__coupling_operation = WRApp.CoSimCoupling(self, self.parameters["coupling"])


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
                         "coupling" : {
                             "coupling_sequence" : [],
                             "convergence_accelerators" : [],
                             "convergence_criteria" : []
                         }
                     }
                     @endcode
        """
        output = super().GetDefaultParameters()
        output.AddString("model_part_name", "")
        output.AddValue("coupling", WRApp.CoSimCoupling.GetDefaultParameters())
        return output


## @}
## @}
