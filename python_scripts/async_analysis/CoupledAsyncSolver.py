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

        # Decide which DataCommunicator to use
        model_part_name = parameters["model_part_name"].GetString()
        self.__data_communicator: KratosMultiphysics.DataCommunicator
        if model_part_name:
            self.__data_communicator = model.GetModelPart(model_part_name).GetCommunicator().GetDataCommunicator()
        else:
            self.__data_communicator = KratosMultiphysics.ParallelEnvironment.GetDefaultDataCommunicator()

        self.__coupling_operation = CoSimCoupling(self,
                                                  model,
                                                  self.__data_communicator,
                                                  self.parameters["coupling"])


    def _Synchronize(self) -> None:
        self.__coupling_operation.Execute()


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
        output.AddValue("coupling", CoSimCoupling.GetDefaultParameters())
        return output


## @}
## @}
