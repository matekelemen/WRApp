"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics
from KratosMultiphysics.kratos_utilities import DeleteDirectoryIfExisting

# --- WRApplication Imports ---
from KratosMultiphysics import WRApplication as WRApp
from Snapshot_test import SetModelPartData, MakeModel

# --- STD Imports ---
import pathlib


class TestCheckpoint(WRApp.TestCase):

    @property
    def test_directory(self) -> pathlib.Path:
        return pathlib.Path("test_checkpoint")


    def setUp(self) -> None:
        DeleteDirectoryIfExisting(str(self.test_directory))
        KratosMultiphysics.Testing.GetDefaultDataCommunicator().Barrier()
        (self.test_directory / "checkpoints").mkdir(parents = True, exist_ok = True)


    def tearDown(self) -> None:
        DeleteDirectoryIfExisting(str(self.test_directory))
        KratosMultiphysics.Testing.GetDefaultDataCommunicator().Barrier()


    def test_Checkpoint(self) -> None:
        _, source_model_part = MakeModel()
        snapshots: "list[WRApp.Snapshot]" = []

        for step in range(2):
            analysis_path = 0
            time = float(step)
            SetModelPartData(source_model_part,
                            step = step,
                            path = analysis_path,
                            time = time)

            # Generate snapshots
            input_parameters = WRApp.HDF5Snapshot.GetInputType().GetDefaultParameters()
            output_parameters = WRApp.HDF5Snapshot.GetOutputType().GetDefaultParameters()

            for parameters in (input_parameters, output_parameters):
                parameters["io_settings"]["file_name"].SetString(str(self.test_directory / f"step_{step}_path_{analysis_path}.h5"))

            #snapshot = WRApp.SnapshotOnDisk.FromModelPart(source_model_part,
            #                                              input_parameters,
            #                                              output_parameters)
            #snapshot.Write(source_model_part)
            #snapshots.append(snapshot)


if __name__ == "__main__":
    WRApp.TestMain()
