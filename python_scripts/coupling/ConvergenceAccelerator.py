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
import re


class ConvergenceAccelerator(WRApp.WRAppClass):
    """ @brief
        @classname ConvergenceAccelerator
    """

    class AcceleratorScope:

        def __init__(self,
                     model_part: KratosMultiphysics.ModelPart,
                     accelerator: CoSimulationConvergenceAccelerator,
                     cache_id: str,
                     variable: WRApp.Typing.Variable):
            self.__model_part = model_part
            self.__accelerator = accelerator
            self.__cache_id = cache_id
            self.__variable = variable


        def __enter__(self) -> "ConvergenceAccelerator.AcceleratorScope":
            """ @brief Equivalent to @ref ConvergenceAccelerator::InitializeNonLinearSolutionStep."""
            self.__SnapshotFactory().Write(self.__model_part)
            self.__accelerator.InitializeNonLinearIteration()
            return self


        def AddTerm(self) -> None:
            """ @brief Push a new term on top of the stack."""
            snapshot = self.__SnapshotFactory()
            snapshot.Erase(self.__model_part.GetCommunicator().GetDataCommunicator())
            snapshot.Write(self.__model_part)


        def Relax(self) -> None:
            """ @brief Equivalent to @ref ConvergenceAccelerator::UpdateSolution."""
            # Compute the residual
            cached = self.__GetCachedExpression()
            residual = self.__GetCurrentExpression() - cached

            # Flatten the residual and write it to a contiguous array
            expression_size = len(residual.GetContainer()) * residual.GetItemComponentCount()
            residual_array = numpy.empty(expression_size)
            cached_array = numpy.empty(expression_size)

            for expression, array in zip((cached, residual), (cached_array, residual_array)):
                KratosMultiphysics.Expression.CArrayExpressionIO.Write(expression, array)

            # Apply the accelerator
            relaxed = cached_array + self.__accelerator.UpdateSolution(residual_array, cached_array)

            # Write relaxed values to the model part
            current_array = relaxed.reshape([len(cached.GetContainer()), *cached.GetItemShape()])
            relaxed_expression = KratosMultiphysics.Expression.NodalExpression(self.__model_part)
            KratosMultiphysics.Expression.CArrayExpressionIO.Move(relaxed_expression, current_array)
            KratosMultiphysics.Expression.VariableExpressionIO.Write(relaxed_expression, self.__variable, True)


        def __exit__(self,
                     exception_type: typing.Optional[typing.Type[Exception]],
                     exception_instance: typing.Optional[Exception],
                     traceback: typing.Optional[types.TracebackType]) -> bool:
            """ @brief Equivalent to @ref ConvergenceAccelerator::FinalizeNonlinearSolutionStep."""
            if any(argument is not None for argument in (exception_type, exception_instance, traceback)):
                return False
            self.__SnapshotFactory().Erase(self.__model_part.GetCommunicator().GetDataCommunicator())
            self.__accelerator.FinalizeNonLinearIteration()
            return True


        def __GetCurrentExpression(self) -> KratosMultiphysics.Expression.NodalExpression:
            """ @brief Populate the input expression with the current values from the model part."""
            output = KratosMultiphysics.Expression.NodalExpression(self.__model_part)
            KratosMultiphysics.Expression.VariableExpressionIO.Read(output,
                                                                    self.__variable,
                                                                    True)
            return output


        def __SnapshotFactory(self) -> WRApp.SnapshotInMemory:
            snapshot_id = WRApp.CheckpointID(self.__model_part.ProcessInfo[KratosMultiphysics.STEP],
                                             self.__model_part.ProcessInfo[WRApp.ANALYSIS_PATH])
            io_parameters = KratosMultiphysics.Parameters("""{
                "nodal_historical_variables" : [],
                "file_name" : ""
            }""")
            io_parameters["nodal_historical_variables"].SetStringArray([self.__variable.Name()])
            io_parameters["file_name"].SetString(self.__cache_id)
            parameters = KratosMultiphysics.Parameters()
            parameters.AddValue("input_parameters", io_parameters)
            parameters.AddValue("output_parameters", io_parameters)
            return WRApp.SnapshotInMemory(snapshot_id, parameters)


        def __GetCachedExpression(self) -> KratosMultiphysics.Expression.NodalExpression:
            output = KratosMultiphysics.Expression.NodalExpression(self.__model_part)
            output.SetExpression(self.__SnapshotFactory().GetExpression(KratosMultiphysics.Expression.ContainerType.NodalHistorical, self.__variable))
            return output


    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        super().__init__()
        parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())
        self.__parameters = parameters
        self.__model_part = model.GetModelPart(parameters["model_part_name"].GetString())
        self.__variable = KratosMultiphysics.KratosGlobals.GetVariable(self.__parameters["variable"].GetString())

        self.__accelerator = CreateConvergenceAccelerator(self.__parameters["parameters"])
        self.__accelerator.Initialize()

        # Convergence accelerators typically need data from the previous time step,
        # which in this case will be stored in an SnapshotInMemory. This snapshot is
        # overwritten on each call to AddTerm, and removed from the cache after the
        # scope is left. The "file name" in the cache is unique to the model part,
        # convergence accelerator type and variable name.
        self.__cache_id = self.__MakeCacheID()


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters("""{
            "model_part_name" : "",
            "variable" : "",
            "parameters" : {}
        }""")


    def __enter__(self) -> "ConvergenceAccelerator.AcceleratorScope":
        self.__cache_id = self.__MakeCacheID()
        self.__accelerator.InitializeSolutionStep()
        return ConvergenceAccelerator.AcceleratorScope(
            self.__model_part,
            self.__accelerator,
            self.__cache_id,
            self.__variable)


    def __exit__(self,
                 exception_type: typing.Optional[typing.Type[Exception]],
                 exception_instance: typing.Optional[Exception],
                 traceback: typing.Optional[types.TracebackType]) -> bool:
        if any(argument is not None for argument in (exception_type, exception_instance, traceback)):
            return False
        self.__accelerator.FinalizeSolutionStep()
        return True


    def __MakeCacheID(self) -> str:
        """ @brief Create a unique ID in the SnapshotInMemoryIO cache."""
        base = f'accelerator_{self.__model_part.Name}_{self.__parameters["variable"].GetString()}'

        # Find the lowest available index
        pattern = re.compile(f"{base}_([0-9]+)")
        index = max((int(pattern.match(hit).group(1)) for hit in WRApp.SnapshotInMemoryIO.Glob(lambda key: pattern.match(key) != None)), default = -1)
        return f"{base}_{index + 1}"
