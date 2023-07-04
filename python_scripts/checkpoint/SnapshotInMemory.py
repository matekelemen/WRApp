""" @author Máté Kelemen"""

__all__ = [
    "SnapshotInMemory",
    "SnapshotInMemoryManager"
]

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
from .Snapshot import Snapshot, SnapshotManager
from .SnapshotInMemoryIO import SnapshotInMemoryInput, SnapshotInMemoryOutput
from KratosMultiphysics import WRApplication as WRApp

# --- STD Imports ---
import typing


## @addtogroup WRApplication
## @{
## @addtogroup checkpointing
## @{


class SnapshotInMemory(Snapshot):
    """ @brief @ref Snapshot that stores/fetches its data in/from memory.
        @classname SnapshotInMemory
    """

    def __init__(self,
                 id: WRApp.CheckpointID,
                 parameters: KratosMultiphysics.Parameters):
        super().__init__(id, parameters)


    def GetExpression(self,
                      container_type: KratosMultiphysics.Expression.ContainerType,
                      variable: WRApp.Typing.Variable) -> KratosMultiphysics.Expression.Expression:
        return self.GetInputType().GetExpression(self._parameters["input_parameters"]["file_name"].GetString(),
                                                 container_type,
                                                 variable)


    def Exists(self) -> bool:
        # Return true if there's a match for CheckPointIDs regardless of model part names
        return bool(self.GetInputType().Glob(lambda pair: pair[1] == self.id))


    def Erase(self, communicator: KratosMultiphysics.DataCommunicator) -> None:
        for file_name in (self._parameters["input_parameters"]["file_name"], self._parameters["output_parameters"]["file_name"]):
            name = file_name.GetString()
            if WRApp.SnapshotInMemoryIO.Exists(name):
                WRApp.SnapshotInMemoryIO.Erase(name)


    def IsValid(self) -> bool:
        return self.Exists()


    @classmethod
    def FromModelPart(cls: typing.Type["SnapshotInMemory"],
                      model_part: KratosMultiphysics.ModelPart,
                      parameters: typing.Union[KratosMultiphysics.Parameters,None] = None) -> "SnapshotInMemory":
        """@brief Deduce variables from an input @ref ModelPart and construct a @ref SnapshotFS.
           @details Input- and output parameters are defaulted if they are not specified by the user.
                    The related file name defaults to "<model_part_name>_step_<step>_path_<path>"."""
        step = model_part.ProcessInfo[KratosMultiphysics.STEP]
        analysis_path = model_part.ProcessInfo[WRApp.ANALYSIS_PATH]

        if parameters is None:
            parameters = cls.GetDefaultParameters()

        if not parameters.Has("input_parameters"):
            parameters.AddValue("input_parameters", cls.GetInputType().GetDefaultParameters())
            parameters["input_parameters"]["file_name"].SetString(f"{model_part.Name}_step_{step}_path_{analysis_path}")
        else:
            parameters["input_parameters"].ValidateAndAssignDefaults(cls.GetInputType().GetDefaultParameters())

        if not parameters.Has("output_parameters"):
            parameters.AddValue("output_parameters", cls.GetOutputType().GetDefaultParameters())
            parameters["output_parameters"]["file_name"].SetString(f"{model_part.Name}_step_{step}_path_{analysis_path}")
        else:
            parameters["output_parameters"].ValidateAndAssignDefaults(cls.GetOutputType().GetDefaultParameters())

        return cls(WRApp.CheckpointID(step, analysis_path), parameters)


    @staticmethod
    def GetInputType() -> typing.Type[SnapshotInMemoryInput]:
        return SnapshotInMemoryInput


    @staticmethod
    def GetOutputType() -> typing.Type[SnapshotInMemoryOutput]:
        return SnapshotInMemoryOutput


    @classmethod
    def GetManagerType(cls) -> typing.Type["SnapshotInMemoryManager"]:
        return SnapshotInMemoryManager



class SnapshotInMemoryManager(SnapshotManager):

    def __init__(self,
                 model_part: KratosMultiphysics.ModelPart,
                 parameters: KratosMultiphysics.Parameters):
        super().__init__(model_part, parameters)

        # Get the snapshot path and prefix patterns, then substitute placeholders that aren't
        # supposed to change throughout the analysis; i.e.: model part name and rank ID
        raw_path_pattern = WRApp.CheckpointPattern(parameters["snapshot_path"].GetString())
        partial_map = {"<model_part_name>" : model_part.Name,
                       "<rank>" : str(model_part.GetCommunicator().GetDataCommunicator().Rank())}
        path_pattern_string = raw_path_pattern.Apply(partial_map)

        # Set up IO parameters
        self.__input_parameters = self._parameters["io"]["input_parameters"]
        self.__output_parameters = self._parameters["io"]["output_parameters"]
        for io in (self.__input_parameters, self.__output_parameters):
            io["file_name"].SetString(path_pattern_string)

        # Set the extractor for the internal journal
        def extractor(model: KratosMultiphysics.Model) -> KratosMultiphysics.Parameters:
            output = KratosMultiphysics.Parameters()
            local_model_part = model.GetModelPart(model_part.Name)
            process_info = local_model_part.ProcessInfo
            output.AddString("model_part_name", local_model_part.Name)
            output.AddInt("step", process_info[KratosMultiphysics.STEP])
            output.AddInt("analysis_path", process_info[WRApp.ANALYSIS_PATH])
            return output
        self._journal.SetExtractor(extractor)


    def Erase(self, id: WRApp.CheckpointID) -> None:
        erase_keys = [key for key, value in SnapshotInMemoryOutput._cache if value["id"] == id]
        for key in erase_keys:
            SnapshotInMemoryOutput.Erase(key)


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        output = super().GetDefaultParameters()
        output.AddString("snapshot_path", "step_<step>")
        return output


    @classmethod
    def _IDFromEntry(cls, journal_entry: KratosMultiphysics.Parameters) -> WRApp.CheckpointID:
        return WRApp.CheckpointID(journal_entry["step"].GetInt(), journal_entry["analysis_path"].GetInt())


    @classmethod
    def _GetSnapshotType(cls) -> typing.Type[Snapshot]:
        return SnapshotInMemory


## @}
## @}
