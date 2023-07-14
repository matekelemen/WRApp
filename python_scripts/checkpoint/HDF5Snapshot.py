"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics
from KratosMultiphysics.kratos_utilities import DeleteFileIfExisting

# --- WRApp Imports --
import KratosMultiphysics.WRApplication as WRApp
from .Snapshot import SnapshotFS, SnapshotManager
from .HDF5SnapshotIO import HDF5SnapshotInput, HDF5SnapshotOutput

# --- STD Imports ---
import typing


## @addtogroup WRApplication
## @{
## @addtogroup checkpointing
## @{


class HDF5SnapshotManager(SnapshotManager):
    """ @brief Snapshot manager specialized for @ref HDF5Snapshot.
        @classname HDF5SnapshotManager
    """

    def __init__(self,
                 model_part: KratosMultiphysics.ModelPart,
                 parameters: KratosMultiphysics.Parameters):
        parameters.AddMissingParameters(self.GetDefaultParameters())
        super().__init__(model_part, parameters)

        # Get the snapshot path and prefix patterns, then substitute placeholders that aren't
        # supposed to change throughout the analysis; i.e.: model part name and rank ID
        raw_path_pattern = WRApp.CheckpointPattern(parameters["snapshot_path"].GetString())
        raw_prefix_pattern = WRApp.CheckpointPattern(parameters["prefix"].GetString())
        partial_map = {"<model_part_name>" : model_part.Name,
                       "<rank>" : str(model_part.GetCommunicator().GetDataCommunicator().Rank())}
        path_pattern_string = raw_path_pattern.Apply(partial_map)
        prefix_pattern_string = raw_prefix_pattern.Apply(partial_map)
        self.__path_pattern = WRApp.CheckpointPattern(path_pattern_string)
        self.__prefix_pattern = WRApp.CheckpointPattern(prefix_pattern_string)

        # Don't allow erasing snapshots if all snapshots are written to the same file
        self.__enable_erase = self.__path_pattern.IsConst()

        # Set up IO parameters
        self.__input_parameters = self._parameters["io"]["input_parameters"]
        self.__output_parameters = self._parameters["io"]["output_parameters"]
        for io in (self.__input_parameters, self.__output_parameters):
            io["prefix"].SetString(prefix_pattern_string)
            io["io_settings"]["file_name"].SetString(path_pattern_string)

        # Set journal extractor functor
        def extractor(model: KratosMultiphysics.Model):
            output = KratosMultiphysics.Parameters()
            local_model_part = model.GetModelPart(model_part.Name)
            process_info = local_model_part.ProcessInfo
            output.AddString("path", self.__path_pattern.Apply(local_model_part))
            output.AddString("prefix", self.__prefix_pattern.Apply(local_model_part))
            output.AddInt("step", process_info[KratosMultiphysics.STEP])
            output.AddInt("analysis_path", process_info[WRApp.ANALYSIS_PATH])
            return output
        self._journal.SetExtractor(extractor)

        # Configuration and filesystem checks
        self.__Check()


    def Get(self, id: WRApp.CheckpointID) -> "HDF5Snapshot":
        return HDF5Snapshot(id, self._parameters["io"])


    def Erase(self, id: WRApp.CheckpointID) -> None:
        file_path = self.__path_pattern.Apply({"<step>" : id.GetStep(),
                                               "<path_id>" : id.GetAnalysisPath()})
        if self.__enable_erase:
            # Mutating operations on the journal can only be executed on the main rank
            if self._model_part.GetCommunicator().GetDataCommunicator().Rank() == 0:
                DeleteFileIfExisting(file_path)
        else:
            KratosMultiphysics.Logger.PrintWarning(f"Blocked request to delete snapshot at {file_path}")


    @classmethod
    def _IDFromEntry(cls, journal_entry: KratosMultiphysics.Parameters) -> WRApp.CheckpointID:
        return WRApp.CheckpointID(journal_entry["step"].GetInt(),
                                  journal_entry["analysis_path"].GetInt())


    @classmethod
    def _GetSnapshotType(cls) -> "typing.Type[HDF5Snapshot]":
        return HDF5Snapshot


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        output = super().GetDefaultParameters()
        output.AddString("snapshot_path", "snapshots.h5")
        output.AddString("prefix", "/snapshot_step_<step>_path_<path_id>")
        return output


    def __Check(self) -> None:
        """@brief Perform init checks to avoid overwriting snapshots."""
        # Require snapshots to have unique paths or prefixes
        # (prevent overwriting older snapshots)
        unique_prefix = not self.__prefix_pattern.IsConst()
        if not (self.__enable_erase or unique_prefix):
            raise ValueError(f"'snapshot_path' or 'prefix' must be a pattern, otherwise snapshots can get overwritten\n{self._parameters}")

        # Check for existing snapshots
        existing_snapshots = [str(path) for path in self.__path_pattern.Glob()]
        if existing_snapshots:
            newline = "\n"
            raise FileExistsError(f"Found existing snapshots at {newline.join(existing_snapshots)}")



class HDF5Snapshot(SnapshotFS):
    """ @brief Class representing a snapshot of a @ref ModelPart state and its associated output file in HDF5 format.
        @classname HDF5Snapshot
    """

    def __init__(self,
                 id: WRApp.CheckpointID,
                 parameters):
        super().__init__(id, parameters)


    def Erase(self, communicator: KratosMultiphysics.DataCommunicator) -> None:
        """@details Don't allow deleting the associated file if all snapshots are written into the same file."""
        is_single_file = all(io.GetPath() == io.GetPath(WRApp.CheckpointID(0,0)) for io in (self._input, self._output))
        if is_single_file:
            raise RuntimeError(f"Single file snapshots cannot be erased individually")
        super().Erase(communicator)


    @staticmethod
    def GetInputType() -> typing.Type[HDF5SnapshotInput]:
        return HDF5SnapshotInput


    @staticmethod
    def GetOutputType() -> typing.Type[HDF5SnapshotOutput]:
        return HDF5SnapshotOutput


    @classmethod
    def GetManagerType(cls) -> typing.Type[HDF5SnapshotManager]:
        return HDF5SnapshotManager


## @}
## @}
