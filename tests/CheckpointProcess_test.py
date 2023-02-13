"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics
from KratosMultiphysics.kratos_utilities import DeleteDirectoryIfExisting

# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp
from Snapshot_test import MakeModel, MakeModelPart, CompareModelParts

# --- STD Imports ---
import pathlib


class TestCheckpointProcess(WRApp.TestCase):

    @property
    def test_directory(self) -> pathlib.Path:
        return pathlib.Path("test_checkpoint_process")


    def setUp(self) -> None:
        if KratosMultiphysics.Testing.GetDefaultDataCommunicator().Rank() == 0:
            DeleteDirectoryIfExisting(str(self.test_directory))
            self.test_directory.mkdir(parents = True, exist_ok = True)
        KratosMultiphysics.Testing.GetDefaultDataCommunicator().Barrier()


    def tearDown(self) -> None:
        #DeleteDirectoryIfExisting(str(self.test_directory))
        KratosMultiphysics.Testing.GetDefaultDataCommunicator().Barrier()


    def test_Defaults(self) -> None:
        parameters = WRApp.CheckpointProcess.GetDefaultParameters()
        parameters["model_part_name"].SetString("test")
        parameters["snapshot_parameters"]["snapshot_path"].SetString(str(self.test_directory / parameters["snapshot_parameters"]["snapshot_path"].GetString()))
        parameters["snapshot_parameters"]["journal_path"].SetString(str(self.test_directory / parameters["snapshot_parameters"]["journal_path"].GetString()))
        self.__Run(parameters)


    def __Run(self, process_parameters: KratosMultiphysics.Parameters) -> None:
        for mdpa_stub in ("simple", "2D"):
            with self.subTest(mdpa_stub):
                try:
                    self.setUp()
                    mdpa_name = f"test_snapshot_{mdpa_stub}"
                    model, model_part = MakeModel(mdpa_name = mdpa_name)
                    process = WRApp.CheckpointProcess(model, process_parameters)

                    process.ExecuteInitialize()
                    for step in range(1, 20):
                        time = step * 2.0
                        model_part.CloneSolutionStep()
                        model_part.ProcessInfo[KratosMultiphysics.STEP] = step
                        model_part.ProcessInfo[KratosMultiphysics.TIME] = time
                        process.ExecuteInitializeSolutionStep()
                        process.ExecuteFinalizeSolutionStep()
                finally:
                    self.tearDown()


if __name__ == "__main__":
    WRApp.TestMain()
