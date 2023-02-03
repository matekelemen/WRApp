"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics
from KratosMultiphysics.kratos_utilities import DeleteDirectoryIfExisting

# --- WRApplication Imports ---
from KratosMultiphysics import WRApplication as WRApp
from Snapshot_test import SetModelPartData, MakeModel, MakeModelPart, CompareModelParts, FlipFlags

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
        #DeleteDirectoryIfExisting(str(self.test_directory))
        KratosMultiphysics.Testing.GetDefaultDataCommunicator().Barrier()


    def test_CheckpointWithHDF5Snapshots(self) -> None:
        for mdpa_stub in ("simple", "2D"):
            with self.subTest(mdpa_stub):
                mdpa_name = f"test_snapshot_{mdpa_stub}"
                model, source_model_part = MakeModel(buffer_size = 2,
                                                     mdpa_name = mdpa_name)
                snapshots: "list[WRApp.Snapshot]" = []

                # Generate snapshots
                for step in range(2):
                    analysis_path = 0
                    time = float(step)
                    SetModelPartData(source_model_part,
                                     step = step,
                                     path = analysis_path,
                                     time = time)

                    input_parameters = WRApp.HDF5Snapshot.GetInputType().GetDefaultParameters()
                    output_parameters = WRApp.HDF5Snapshot.GetOutputType().GetDefaultParameters()

                    for parameters in (input_parameters, output_parameters):
                        parameters["io_settings"]["file_name"].SetString(str(self.test_directory / f"step_{step}_path_{analysis_path}.h5"))

                    snapshot = WRApp.HDF5Snapshot.FromModelPart(source_model_part,
                                                                input_parameters,
                                                                output_parameters)
                    snapshot.Write(source_model_part)
                    snapshots.append(snapshot)

                # Construct the checkpoint and create a target model part to read into
                checkpoint = WRApp.Checkpoint(snapshots)
                target_model_part = MakeModelPart(model,
                                                  name = "target",
                                                  buffer_size = 2,
                                                  mdpa_name = mdpa_name)

                # Clobber the target model part and its buffer
                for step in range(98, 102):
                    SetModelPartData(target_model_part,
                                     step = step,
                                     path = 0,
                                     time = float(step))
                FlipFlags(target_model_part.Nodes)
                FlipFlags(target_model_part.Elements)
                FlipFlags(target_model_part.Conditions)

                # Load the checkpoint and compare the model parts
                checkpoint.Load(target_model_part)
                CompareModelParts(source_model_part,
                                  target_model_part,
                                  self,
                                  buffer_level = 2)


if __name__ == "__main__":
    WRApp.TestMain()
