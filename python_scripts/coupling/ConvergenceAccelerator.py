""" @author Máté Kelemen"""

__all__ = ["ConvergenceAccelerator"]

# --- External Imports ---
import numpy

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
from KratosMultiphysics import WRApplication as WRApp

# --- CoSim Imports ---
from KratosMultiphysics.CoSimulationApplication.base_classes.co_simulation_convergence_accelerator import CoSimulationConvergenceAccelerator
from KratosMultiphysics.CoSimulationApplication.factories.convergence_accelerator_factory import CreateConvergenceAccelerator

# --- STD Imports ---
import typing
import types


class ConvergenceAccelerator(WRApp.WRAppClass):
    """ @brief
        @classname ConvergenceAccelerator
        @details Default parameters:
                 @code
                 {
                    "dataset" : {           // <== dataset to relax
                        "type" : "",        // <== dataset type
                        "parameters" : {}   // <== parameters to pass on to the dataset's constructor
                    },
                    "parameters" : {}       // <== parameters to pass to the accelerator factory
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
        self.__dataset: WRApp.Dataset = WRApp.RegisteredClassFactory(parameters["dataset"]["type"].GetString(),
                                                                     model,
                                                                     parameters["dataset"]["parameters"])

        self.__accelerator = CreateConvergenceAccelerator(parameters["parameters"])
        self.__accelerator.Initialize()


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters("""{
            "dataset" : {
                "type" : "",
                "parameters" : {}
            },
            "parameters" : {}
        }""")


    def __enter__(self) -> "ConvergenceAccelerator.AcceleratorScope":
        self.__accelerator.InitializeSolutionStep()
        return ConvergenceAccelerator.AcceleratorScope(self.__dataset, self.__accelerator)


    def __exit__(self,
                 exception_type: typing.Optional[typing.Type[Exception]],
                 exception_instance: typing.Optional[Exception],
                 traceback: typing.Optional[types.TracebackType]) -> bool:
        if any(argument is not None for argument in (exception_type, exception_instance, traceback)):
            return False
        self.__accelerator.FinalizeSolutionStep()
        return True


    class AcceleratorScope:

        def __init__(self,
                     dataset: "WRApp.Dataset",
                     accelerator: CoSimulationConvergenceAccelerator):
            self.__dataset = dataset
            self.__accelerator = accelerator


        def __enter__(self) -> "ConvergenceAccelerator.AcceleratorScope":
            """ @brief Equivalent to @ref ConvergenceAccelerator::InitializeNonLinearSolutionStep."""
            self.__dataset.Fetch() # <== save the current state of the dataset
            self.__accelerator.InitializeNonLinearIteration()
            return self


        def AddTerm(self) -> None:
            self.__dataset.Fetch()


        def Relax(self) -> None:
            """ @brief Equivalent to @ref ConvergenceAccelerator::UpdateSolution."""
            expression_size = self.__dataset.expression.NumberOfEntities() * self.__dataset.expression.GetItemComponentCount()

            # Copy the dataset in its cached state
            cached = self.__dataset.expression
            cached_array = numpy.empty(expression_size)
            KratosMultiphysics.Expression.CArrayExpressionIO.Output(cached_array).Execute(cached)

            # Compute the residual
            self.__dataset.Fetch()
            residual = self.__dataset.expression - cached

            # Flatten the residual and write it to a contiguous array
            residual_array = numpy.empty(expression_size)
            KratosMultiphysics.Expression.CArrayExpressionIO.Output(residual_array).Execute(residual)

            # Apply the accelerator
            relaxed_array = cached_array + self.__accelerator.UpdateSolution(residual_array, cached_array)

            # Write relaxed values to the model part
            current_array = relaxed_array.reshape([cached.NumberOfEntities(), *cached.GetItemShape()])
            self.__dataset.expression = KratosMultiphysics.Expression.CArrayExpressionIO.Input(
                current_array,
                cached.NumberOfEntities(),
                cached.GetItemShape()).Execute()
            self.__dataset.Assign()


        def __exit__(self,
                     exception_type: typing.Optional[typing.Type[Exception]],
                     exception_instance: typing.Optional[Exception],
                     traceback: typing.Optional[types.TracebackType]) -> bool:
            """ @brief Equivalent to @ref ConvergenceAccelerator::FinalizeNonlinearSolutionStep."""
            if any(argument is not None for argument in (exception_type, exception_instance, traceback)):
                return False
            self.__accelerator.FinalizeNonLinearIteration()
            return True
