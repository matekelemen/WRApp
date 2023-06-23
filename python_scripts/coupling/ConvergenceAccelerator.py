""" @author Máté Kelemen"""

__all__ = ["ConvergenceAccelerator"]

# --- External Imports ---
import numpy

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
from KratosMultiphysics import WRApplication as WRApp

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
                     expression: KratosMultiphysics.Expression.NodalExpression,
                     accelerator: KratosMultiphysics.ConvergenceAccelerator,
                     cache_id: str,
                     variable: WRApp.Typing.Variable):
            self.__expression = expression
            self.__accelerator = accelerator
            self.__cache_id = cache_id
            self.__variable = variable
            self.__UpdateExpression(self.__expression)
            self.__accelerated = KratosMultiphysics.Vector(len(self.__expression.GetContainer()) * self.__expression.GetItemComponentCount())


        def __enter__(self) -> "ConvergenceAccelerator.AcceleratorScope":
            """ @brief Equivalent to @ref ConvergenceAccelerator::InitializeNonLinearSolutionStep."""
            snapshot = self.__SnapshotFactory()
            snapshot.Write(self.__expression.GetModelPart())
            return self


        def AddTerm(self) -> None:
            """ @brief Equivalent to @ref ConvergenceAccelerator::UpdateSolution."""
            # Compute the residual
            current = KratosMultiphysics.Expression.NodalExpression(self.__expression.GetModelPart())
            self.__UpdateExpression(current)
            residual = current - self.__expression

            # Flatten the residual and write it to a numpy array
            expression_size = len(residual.GetContainer()) * residual.GetItemComponentCount()
            residual_array = KratosMultiphysics.Vector(expression_size)
            KratosMultiphysics.Expression.CArrayExpressionIO.Write(residual.Reshape([residual.GetItemComponentCount()]), residual_array)

            self.__accelerator.UpdateSolution(residual_array, self.__accelerated)


        def __exit__(self,
                     exception_type: typing.Optional[typing.Type[Exception]],
                     exception_instance: typing.Optional[Exception],
                     traceback: typing.Optional[types.TracebackType]) -> bool:
            """ @brief Equivalent to @ref ConvergenceAccelerator::FinalizeNonlinearSolutionStep."""
            if any(argument is not None for argument in (exception_type, exception_instance, traceback)):
                return False
            self.__UpdateExpression(self.__expression)
            self.__SnapshotFactory().Erase(self.__expression.GetModelPart().GetCommunicator().GetDataCommunicator())
            return True


        def __UpdateExpression(self, expression: KratosMultiphysics.Expression.NodalExpression) -> None:
            """ @brief Populate the input expression with the current values from the model part."""
            KratosMultiphysics.Expression.VariableExpressionIO.Read(expression,
                                                                    self.__variable,
                                                                    True)


        def __SnapshotFactory(self) -> WRApp.SnapshotInMemory:
            model_part = self.__expression.GetModelPart()
            snapshot_id = WRApp.CheckpointID(model_part.ProcessInfo[KratosMultiphysics.STEP],
                                             model_part.ProcessInfo[WRApp.ANALYSIS_PATH])
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


    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        super().__init__()
        parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())
        self.__parameters = parameters
        self.__model_part = model.GetModelPart(parameters["model_part_name"].GetString())
        self.__variable = KratosMultiphysics.KratosGlobals.GetVariable(self.__parameters["variable"].GetString())

        try: # Try constructing the accelerator from the FSIApplication
            from KratosMultiphysics import FSIApplication
            from KratosMultiphysics.FSIApplication.convergence_accelerator_factory import CreateConvergenceAccelerator
        except ImportError as exception: # Fall back to CoSim accelerators
            KratosMultiphysics.Logger.PrintInfo("FSIApplication is not available; looking for convergence accelerators elsewhere")
            from KratosMultiphysics import CoSimulationApplication
            from KratosMultiphysics.CoSimulationApplication.factories.convergence_accelerator_factory import CreateConvergenceAccelerator
        self.__accelerator_factory = CreateConvergenceAccelerator
        self.__accelerator: typing.Optional[KratosMultiphysics.ConvergenceAccelerator] = None # <== gets constructed in __enter__ and destroyed in __exit__

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
        # Check whether the reserved spot in the cache is still available
        if WRApp.SnapshotInMemoryIO.Exists(self.__cache_id):
            raise FileExistsError(f"In-memory snapshot for {self.__cache_id} already exists")

        self.__accelerator = self.__accelerator_factory(self.__parameters["parameters"])
        self.__accelerator.Initialize()
        self.__accelerator.InitializeSolutionStep()

        return ConvergenceAccelerator.AcceleratorScope(
            KratosMultiphysics.Expression.NodalExpression(self.__model_part),
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
        self.__accelerator = None
        WRApp.SnapshotInMemoryIO.Erase(self.__cache_id)
        return True


    def __MakeCacheID(self) -> str:
        """ @brief Create a unique ID in the SnapshotInMemoryIO cache."""
        base = f'accelerator_{self.__model_part.Name}_{self.__parameters["variable"].GetString()}'

        # Find the lowest available index
        pattern = re.compile(f"{base}_([0-9]+)")
        index = max((int(pattern.match(hit).group(1)) for hit in WRApp.SnapshotInMemoryIO.Glob(lambda key: pattern.match(key) != None)), default = -1)
        return f"{base}_{index + 1}"
