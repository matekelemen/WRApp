"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics
from KratosMultiphysics.kratos_utilities import DeleteDirectoryIfExisting

# --- WRApplication Imports ---
from KratosMultiphysics import WRApplication as WRApp
from KratosMultiphysics.WRApplication.MPIUtils import MPIUtils
from Snapshot_test import SetModelPartData, MakeModel, MakeModelPart, CompareModelParts, FlipFlags
from MDPAGenerator import MDPAGenerator

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
                try:
                    self.setUp()
                    self.RunModel(mdpa_stub)
                finally:
                    self.tearDown()


    def RunModel(self, mdpa_stub: str) -> None:
        mdpa_name = f"test_snapshot_{mdpa_stub}"
        generator = MDPAGenerator()
        model, source_model_part = MakeModel(buffer_size = 2,
                                             mdpa_name = mdpa_name)

        # Generate snapshots
        snapshots: "list[WRApp.Snapshot]" = []
        snapshot_parameters = WRApp.HDF5Snapshot.GetDefaultParameters()
        for io in (snapshot_parameters["input_parameters"], snapshot_parameters["output_parameters"]):
            io["io_settings"]["file_name"].SetString(str(self.test_directory / "snapshots.h5"))
            io["nodal_historical_variables"].SetStringArray([variable.Name() for variable in generator.historical_nodal_variables])
            io["nodal_variables"].SetStringArray([variable.Name() for variable in generator.nodal_variables])
            io["nodal_flags"].SetStringArray(MPIUtils.ExtractNodalFlagNames(source_model_part))
            io["element_variables"].SetStringArray([variable.Name() for variable in generator.element_variables])
            io["element_flags"].SetStringArray(MPIUtils.ExtractElementFlagNames(source_model_part))
            io["condition_variables"].SetStringArray([variable.Name() for variable in generator.condition_variables])
            io["condition_flags"].SetStringArray(MPIUtils.ExtractConditionFlagNames(source_model_part))

        for step in range(2):
            analysis_path = 0
            time = float(step)
            source_model_part.CloneSolutionStep()
            SetModelPartData(source_model_part,
                             step = step,
                             path = analysis_path,
                             time = time)

            snapshot = WRApp.HDF5Snapshot.FromModelPart(source_model_part,
                                                        snapshot_parameters)
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
                          self)


if __name__ == "__main__":
    WRApp.TestMain()
