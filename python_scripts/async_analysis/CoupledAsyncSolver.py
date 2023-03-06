""" @author Máté Kelemen"""

__all__ = [
    "CoupledAsyncSolver"
]

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
from .AsyncSolver import AsyncSolver
from .CoSimCoupling import CoSimCoupling


## @addtogroup WRApplication
## @{
## @addtogroup AsyncAnalysis
## @{


class CoupledAsyncSolver(AsyncSolver):
    """ @brief @ref AsyncSolver with coupling directives from @ref CoSimulationApplication.
        @classname CoupledAsyncSolver
        @details This class shoves most functionality from @ref CoSimulationCoupledSolver
                 into the interface set by @AsyncSolver.
    """

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        super().__init__(model, parameters)
        self.__coupling_operation = CoSimCoupling(model,
                                                  self.model_part.GetCommunicator().GetDataCommunicator(),
                                                  self.parameters["coupling"])


    def _Synchronize(self) -> None:
        super()._Synchronize()
        self.__coupling_operation.Execute()


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        """ @code
            {
                ...,
                "coupling" : {
                    "interface_datasets" : []
                    "transform_operators" : {},
                    "coupling_sequence" : [],
                    "verbosity" : 2
                },
                "predictors" : []
            }
            @endcode
        """
        output = super().GetDefaultParameters()
        output.AddValue("coupling", CoSimCoupling.GetDefaultParameters())
        return output


## @}
## @}
