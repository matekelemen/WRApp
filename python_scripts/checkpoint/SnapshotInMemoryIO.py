""" @author Máté Kelemen"""

__all__ = [
    "SnapshotInMemoryIO",
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
import fnmatch


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
    #       "data" : {container_type, {variable_name : container_expression}},
    #       "flags" : {"nodes" : vector_of_flags, "elements" : vector_of_flags, "conditions" : vector_of_flags}
    #       "process_info" : {variable_name : value}
    #   }
    _cache = {}


    def __init__(self, parameters: KratosMultiphysics.Parameters):
        super().__init__(parameters)


    @classmethod
    def Erase(cls, file_name: str) -> None:
        del cls._cache[file_name]


    @classmethod
    def Exists(cls, file_name: str) -> bool:
        return file_name in cls._cache


    @classmethod
    def Glob(cls, pattern: str) -> "list[str]":
        return fnmatch.filter(cls._cache.keys(), pattern)


    @classmethod
    def Clear(cls) -> None:
        cls._cache.clear()


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        output = super().GetDefaultParameters()
        output.AddString("file_name", "")
        return output


    class Operation(KratosMultiphysics.Operation):
        """ @brief Base class for interacting with the static cache of @ref SnapshotInMemoryIO."""

        _container_map = {
            "nodal_historical_variables"    : KratosMultiphysics.Globals.DataLocation.NodeHistorical,
            "nodal_variables"               : KratosMultiphysics.Globals.DataLocation.NodeNonHistorical,
            "element_variables"             : KratosMultiphysics.Globals.DataLocation.Element,
            "condition_variables"           : KratosMultiphysics.Globals.DataLocation.Condition
        }

        _expression_map = {
            KratosMultiphysics.Globals.DataLocation.NodeHistorical : KratosMultiphysics.Expression.NodalExpression,
            KratosMultiphysics.Globals.DataLocation.NodeNonHistorical : KratosMultiphysics.Expression.NodalExpression,
            KratosMultiphysics.Globals.DataLocation.Element : KratosMultiphysics.Expression.ElementExpression,
            KratosMultiphysics.Globals.DataLocation.Condition : KratosMultiphysics.Expression.ConditionExpression
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

    def __init__(self, parameters: KratosMultiphysics.Parameters):
        super().__init__(parameters)


    @classmethod
    def GetEntry(cls, file_name: str) -> dict:
        entry = cls._cache.get(file_name, None)
        if entry == None:
            newline = '\n'
            raise KeyError(f"No in-memory snapshot found at '{file_name}'. The following items are in the current cache:{newline.join(key for key in cls._cache.keys())}")
        return entry


    @classmethod
    def GetExpression(cls,
                      file_name: str,
                      container_type: KratosMultiphysics.Globals.DataLocation,
                      variable: WRApp.Typing.Variable) -> KratosMultiphysics.Expression.Expression:
        return cls.GetEntry(file_name)["data"][container_type][variable.Name()]


    class Operation(SnapshotInMemoryIO.Operation):
        """ @brief Read data from the static cache of @ref SnapshotInMemoryIO."""


        def __init__(self,
                     model_part: KratosMultiphysics.ModelPart,
                     parameters: KratosMultiphysics.Parameters):
            super().__init__(model_part, parameters)


        def Execute(self) -> None:
            file_name = WRApp.CheckpointPattern(self._parameters["file_name"].GetString()).Apply(self._model_part)
            entry = SnapshotInMemoryIO._cache.get(file_name, None)

            if entry is None:
                raise RuntimeError(f"No in-memory snapshot found at '{file_name}'")

            # Assign data from nodes, elements, and conditions
            for container_name, variable_names in self._parameters.items():

                # Assign data from variables
                if container_name in self._container_map:
                    names = variable_names.GetStringArray()
                    container_type = self._container_map[container_name]

                    # Fetch data from the static cache
                    for variable_name in names:
                        variable = KratosMultiphysics.KratosGlobals.GetVariable(variable_name)
                        expression = self._expression_map[container_type](self._model_part)
                        expression.SetExpression(entry["data"][container_type][variable_name])

                        is_historical = container_type == KratosMultiphysics.Globals.DataLocation.NodeHistorical

                        # Assign data to the model part
                        if is_historical or container_type == KratosMultiphysics.Globals.DataLocation.NodeNonHistorical:
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
            file_name = WRApp.CheckpointPattern(self._parameters["file_name"].GetString()).Apply(self._model_part)
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
                            # Construct a new expression
                            expression = self._expression_map[container_type](self._model_part)
                            variable = KratosMultiphysics.KratosGlobals.GetVariable(variable_name)
                            is_historical = container_type == KratosMultiphysics.Globals.DataLocation.NodeHistorical

                            # Read data from the model part into the expression
                            if is_historical or container_type == KratosMultiphysics.Globals.DataLocation.NodeNonHistorical:
                                KratosMultiphysics.Expression.VariableExpressionIO.Read(expression, variable, is_historical)
                            else:
                                KratosMultiphysics.Expression.VariableExpressionIO.Read(expression, variable)

                            # Store the loaded expression in the new cache entry
                            map[variable_name] = expression.GetExpression()

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
