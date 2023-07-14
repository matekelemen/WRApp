""" @author Máté Kelemen"""

__all__ = [
    "ConvergenceCriterion"
]

# --- External Imports ---
import numpy

# --- Core Imports ---
import KratosMultiphysics

# --- CoSimulation Imports ---
from KratosMultiphysics.CoSimulationApplication.factories.convergence_criterion_factory import CreateConvergenceCriterion
from KratosMultiphysics.CoSimulationApplication.base_classes.co_simulation_convergence_criteria import CoSimulationConvergenceCriteria

# --- WRApp Imports ---
from KratosMultiphysics import WRApplication as WRApp

# --- STD Imports ---
import typing
import types


class ConvergenceCriterion(WRApp.WRAppClass):
    """ @brief Wrapper for cosim convergence criteria.
        @classname ConvergenceCriterion
        @details Default parameters:
                 @code
                 {
                    "datatset" : {
                        "type" : "",        // <== full name of the dataset type in the runtime registry
                        "parameters" : {}   // <== parameters passed to the constructor of the dataset
                    },
                    "criterion" : {}        // <== parameters passed on to the cosimulation convergence criteria factory
                 }
                 @endcode
    """

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        super().__init__()
        default_parameters = self.GetDefaultParameters()
        parameters.ValidateAndAssignDefaults(default_parameters)
        dataset_parameters = parameters["dataset"]
        dataset_parameters.ValidateAndAssignDefaults(default_parameters["dataset"])

        self.__dataset: WRApp.Dataset = WRApp.RegisteredClassFactory(dataset_parameters["type"].GetString(),
                                                                     model,
                                                                     dataset_parameters["parameters"])
        self.__criterion: CoSimulationConvergenceCriteria = CreateConvergenceCriterion(parameters["criterion"])
        self.__criterion.Initialize()


    def __enter__(self) -> "ConvergenceCriterion":
        self.__dataset.Fetch()
        return self


    def AddTerm(self) -> None:
        #self.__dataset.Fetch() # <== HasConverged already fetched the last iteration
        pass


    def HasConverged(self) -> bool:
        expression_size = self.__dataset.expression.NumberOfEntities() * self.__dataset.expression.GetItemComponentCount()

        # Copy the dataset in its cached state
        cached = self.__dataset.expression

        # Compute residual
        self.__dataset.Fetch()
        residual = self.__dataset.expression - cached

        residual_array = numpy.empty(expression_size)
        KratosMultiphysics.Expression.CArrayExpressionIO.Output(residual_array).Execute(residual)

        # Copy the dataset in its current state
        current_array = numpy.empty(expression_size)
        KratosMultiphysics.Expression.CArrayExpressionIO.Output(current_array).Execute(self.__dataset.expression)

        # Check criterion
        return self.__criterion.IsConverged(residual_array, current_array)


    def __exit__(self,
                 exception_type: typing.Optional[typing.Type[Exception]],
                 exception_instance: typing.Optional[Exception],
                 traceback: typing.Optional[types.TracebackType]) -> bool:
        if any(argument is not None for argument in (exception_type, exception_instance, traceback)):
            return False
        return True


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters("""{
            "dataset" : {
                "type" : "",
                "parameters" : {}
            },
            "criterion" : {}
        }""")
