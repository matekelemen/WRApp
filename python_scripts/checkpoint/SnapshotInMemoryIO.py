""" @author Máté Kelemen"""

__all__ = [
    "SnapshotInMemoryInput",
    "SnapshotInMemoryOutput"
]

# --- External Imports ---
import numpy

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
from .SnapshotIO import SnapshotIO
from KratosMultiphysics import WRApplication as WRApp

# --- STD Imports ---
import typing


## @addtogroup WRApplication
## @{
## @addtogroup checkpointing
## @{


class SnapshotInMemoryIO(SnapshotIO):
    """ @brief Base class for @ref Snapshot input/output operations in memory.
        @classname SnapshotInMemory
    """

    # Key: path
    # Value: {
    #       "id" : checkpoint_id,
    #       "data" : {container_type, {variable_name : numpy_array}},
    #       "flags" : {"nodes" : vector_of_flags, "elements" : vector_of_flags, "conditions" : vector_of_flags}
    #       "process_info" : {variable_name : numpy_array}
    #   }
    _cache = {}


    def __init__(self, parameters: KratosMultiphysics.Parameters):
        super().__init__(parameters)


    @classmethod
    def Erase(cls, path: str) -> None:
        del cls._cache[path]


    @classmethod
    def Glob(cls, predicate: "typing.Callable[[str],bool]") -> "list[tuple[str,WRApp.CheckpointID]]":
        return [key for key in cls._cache.keys() if predicate(key)]


    @classmethod
    def Clear(cls) -> None:
        cls._cache.clear()


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        """ @code
            {
                "nodal_historical_variables" : [],
                "nodal_variables" : [],
                "nodal_flags" : [],
                "element_variables" : [],
                "element_flags" : [],
                "condition_variables" : [],
                "condition_flags" : [],
                "file_name" : ""
            }
            @endcode
        """
        output = super().GetDefaultParameters()
        output.AddString("file_name", "")
        return output


    class Operation(KratosMultiphysics.Operation):
        """ @brief Base class for interacting with the static cache of @ref SnapshotInMemoryIO."""

        _container_map = {
            "nodal_historical_variables"    : KratosMultiphysics.Expression.ContainerType.NodalHistorical,
            "nodal_variables"               : KratosMultiphysics.Expression.ContainerType.NodalNonHistorical,
            "element_variables"             : KratosMultiphysics.Expression.ContainerType.ElementNonHistorical,
            "condition_variables"           : KratosMultiphysics.Expression.ContainerType.ConditionNonHistorical
        }

        _expression_map = {
            KratosMultiphysics.Expression.ContainerType.NodalHistorical : KratosMultiphysics.Expression.NodalExpression,
            KratosMultiphysics.Expression.ContainerType.NodalNonHistorical : KratosMultiphysics.Expression.NodalNonHistoricalExpression,
            KratosMultiphysics.Expression.ContainerType.ElementNonHistorical : KratosMultiphysics.Expression.ElementExpression,
            KratosMultiphysics.Expression.ContainerType.ConditionNonHistorical : KratosMultiphysics.Expression.ConditionExpression
        }


        def __init__(self,
                     model_part: KratosMultiphysics.ModelPart,
                     parameters: KratosMultiphysics.Parameters):
            super().__init__()
            self._parameters = parameters
            self._parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())
            self._model_part = model_part


        @classmethod
        def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
            return SnapshotInMemoryIO.GetDefaultParameters()



class SnapshotInMemoryInput(SnapshotInMemoryIO):
    """ @brief Implements @ref Snapshot input operations in memory."""

    class Operation(SnapshotInMemoryIO.Operation):
        """ @brief Read data from the static cache of @ref SnapshotInMemoryIO."""


        def __init__(self,
                     model_part: KratosMultiphysics.ModelPart,
                     parameters: KratosMultiphysics.Parameters):
            super().__init__(model_part, parameters)


        def Execute(self) -> None:
            file_name = self._parameters["file_name"].GetString()
            entry = SnapshotInMemoryIO._cache.get(file_name, None)

            if entry is None:
                raise RuntimeError(f"No in-memory snapshot found at '{file_name}'")

            map: "dict[str,numpy.ndarray]"

            # Assign data from nodes, elements, and conditions
            for container_name, variable_names in self._parameters.items():

                # Assign data from variables
                if container_name in self._container_map:
                    names = variable_names.GetStringArray()
                    container_type = self._container_map[container_name]

                    # Fetch data from the static cache
                    for variable_name in names:
                        expression = self._expression_map[container_type](self._model_part)
                        KratosMultiphysics.Expression.CArrayExpressionIO.Read(expression, entry["data"][container_type][variable_name])
                        variable = KratosMultiphysics.KratosGlobals.GetVariable(variable_name)
                        is_historical = container_type == KratosMultiphysics.Expression.ContainerType.NodalHistorical

                        # Assign data to the model part
                        if is_historical or container_type == KratosMultiphysics.Expression.ContainerType.NodalNonHistorical:
                            KratosMultiphysics.Expression.VariableExpressionIO.Write(expression,
                                                                                     variable,
                                                                                     is_historical)
                        else:
                            KratosMultiphysics.Expression.VariableExpressionIO.Write(expression,
                                                                                     variable)
                # Assign data from flags
                elif "flags" in container_name:
                    names = variable_names.GetStringArray()
                    if container_name == "nodal_flags":
                        container = self._model_part.Nodes
                    elif container_name == "element_flags":
                        container = self._model_part.Elements
                    elif container_name == "condition_flags":
                        container = self._model_part.Conditions
                    else:
                        raise ValueError(f"Invalid container '{container_name}'")

                    # Collect flags
                    mask = KratosMultiphysics.Flags()
                    if names:
                        for flag_name in names:
                            flag: KratosMultiphysics.Flags = KratosMultiphysics.KratosGlobals.GetFlag(flag_name)
                            mask |= flag

                    WRApp.Utils.SetFlags(container, entry[container_name], mask)

            # Assign data from process info
            for variable_name, value in entry["process_info"].items():
                variable = KratosMultiphysics.KratosGlobals.GetVariable(variable_name)
                self._model_part.ProcessInfo[variable] = value


    def _GetOperation(self, model_part: KratosMultiphysics.ModelPart) -> KratosMultiphysics.Operation:
        return self.Operation(model_part, self._parameters)



class SnapshotInMemoryOutput(SnapshotInMemoryIO):
    """ @brief Implements @ref Snapshot output operations in memory."""

    def __init__(self, parameters: KratosMultiphysics.Parameters):
        super().__init__(parameters)


    class Operation(SnapshotInMemoryIO.Operation):
        """ @brief Write data to the static cache of @ref SnapshotInMemoryIO."""

        def __init__(self,
                     model_part: KratosMultiphysics.ModelPart,
                     parameters: KratosMultiphysics.Parameters):
            super().__init__(model_part, parameters)


        def Execute(self) -> None:
            file_name = self._parameters["file_name"].GetString()
            if file_name in SnapshotInMemoryIO._cache:
                raise FileExistsError(f"An in-memory snapshot already exists at '{file_name}'")

            entry = {"id" : WRApp.CheckpointID(self._model_part.ProcessInfo[KratosMultiphysics.STEP],
                                               self._model_part.ProcessInfo[WRApp.ANALYSIS_PATH]),
                     "data" : dict(),
                     "nodal_flags" : WRApp.Utils.FlagArray,
                     "element_flags" : WRApp.Utils.FlagArray,
                     "condition_flags" : WRApp.Utils.FlagArray,
                     "process_info" : dict()}

            # Collect data from nodes, elements, and conditions
            for container_name, variable_names in self._parameters.items():
                if container_name in self._container_map:
                    names = variable_names.GetStringArray()

                    if names:
                        container_type = self._container_map[container_name]

                        map = dict()
                        for variable_name in names:
                            expression = self._expression_map[container_type](self._model_part)
                            variable = KratosMultiphysics.KratosGlobals.GetVariable(variable_name)
                            is_historical = container_type == KratosMultiphysics.Expression.ContainerType.NodalHistorical

                            # Read data from the model part into the expression
                            if is_historical or container_type == KratosMultiphysics.Expression.ContainerType.NodalNonHistorical:
                                KratosMultiphysics.Expression.VariableExpressionIO.Read(expression, variable, is_historical)
                            else:
                                KratosMultiphysics.Expression.VariableExpressionIO.Read(expression, variable)

                            # Write the collected data to a c-array
                            number_of_items = len(expression.GetContainer())
                            stride = expression.GetItemComponentCount()
                            array = numpy.empty(number_of_items if stride == 1 else (number_of_items, *expression.GetItemShape()))
                            KratosMultiphysics.Expression.CArrayExpressionIO.Write(expression, array)
                            map[variable_name] = array

                        entry["data"][container_type] = map
                elif "flags" in container_name:
                    names = variable_names.GetStringArray()
                    if container_name == "nodal_flags":
                        container = self._model_part.Nodes
                    elif container_name == "element_flags":
                        container = self._model_part.Elements
                    elif container_name == "condition_flags":
                        container = self._model_part.Conditions
                    else:
                        raise ValueError(f"Invalid container '{container_name}'")

                    # Collect flags
                    mask = KratosMultiphysics.Flags()
                    if names:
                        for flag_name in names:
                            flag: KratosMultiphysics.Flags = KratosMultiphysics.KratosGlobals.GetFlag(flag_name)
                            mask |= flag

                    entry[container_name] = WRApp.Utils.GetFlags(container, mask)


            # Collect process info data
            for variable_name in WRApp.Utils.GetDataValueContainerKeys(self._model_part.ProcessInfo):
                variable = KratosMultiphysics.KratosGlobals.GetVariable(variable_name)
                entry["process_info"][variable_name] = self._model_part.ProcessInfo[variable]

            SnapshotInMemoryIO._cache[file_name] = entry


    def _GetOperation(self, model_part: KratosMultiphysics.ModelPart) -> KratosMultiphysics.Operation:
        return self.Operation(model_part, self._parameters)


## @}
## @}
