"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics
from KratosMultiphysics.kratos_utilities import DeleteDirectoryIfExisting

# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp
from Snapshot_test import MakeModel, MakeModelPart, CompareModelParts

# --- STD Imports ---
import pathlib
import typing


def _Run(test_case: WRApp.TestCase,
         process_parameters: KratosMultiphysics.Parameters,
         check: "typing.Callable[[KratosMultiphysics.ModelPart],None]" = lambda mp: None) -> None:
    for mdpa_stub in ("simple", "2D"):
        with test_case.subTest(mdpa_stub):
            try:
                test_case.setUp()
                mdpa_name = f"test_snapshot_{mdpa_stub}"
                model, model_part = MakeModel(mdpa_name = mdpa_name)
                process = WRApp.CheckpointProcess(model, process_parameters)
                process.Initialize()

                process.ExecuteInitialize()
                for step in range(1, 50):
                    step = model_part.ProcessInfo[KratosMultiphysics.STEP]
                    model_part.CloneSolutionStep()
                    model_part.ProcessInfo[KratosMultiphysics.STEP] = step + 1
                    model_part.ProcessInfo[KratosMultiphysics.TIME] = step * 2.0
                    process.ExecuteInitializeSolutionStep()
                    process.ExecuteFinalizeSolutionStep()

                check(model_part)
            finally:
                test_case.tearDown()


class TestCheckpointProcess(WRApp.TestCase):

    @property
    def test_directory(self) -> pathlib.Path:
        return pathlib.Path("test_checkpoint_process").absolute()


    def setUp(self) -> None:
        if KratosMultiphysics.Testing.GetDefaultDataCommunicator().Rank() == 0:
            DeleteDirectoryIfExisting(str(self.test_directory))
            self.test_directory.mkdir(parents = True, exist_ok = True)
        KratosMultiphysics.Testing.GetDefaultDataCommunicator().Barrier()


    def tearDown(self) -> None:
        WRApp.SnapshotInMemoryIO.Clear()
        DeleteDirectoryIfExisting(str(self.test_directory))
        KratosMultiphysics.Testing.GetDefaultDataCommunicator().Barrier()


    def test_Defaults(self) -> None:
        parameters = WRApp.CheckpointProcess.GetDefaultParameters()
        snapshot_path_pattern = self.test_directory / "step_<step>.h5"
        parameters["snapshot_parameters"].AddString("snapshot_path", str(snapshot_path_pattern))
        parameters["model_part_name"].SetString("test")
        parameters["snapshot_parameters"].AddString("journal_path", str(self.test_directory / "journal"))

        _Run(self, parameters)


    def test_WritePredicate(self) -> None:
        parameters = WRApp.CheckpointProcess.GetDefaultParameters()
        parameters["model_part_name"].SetString("test")
        parameters["write_predicate"]["type"].SetString("WRApplication.StepIntervalPredicate")
        parameters["write_predicate"]["parameters"] = KratosMultiphysics.Parameters(R"""[
            {"model_part_name" : "test"},
            {},
            {},
            {"interval" : [3, 5]}
        ]""")
        snapshot_path_pattern = self.test_directory / "step_<step>.h5"
        parameters["snapshot_parameters"].AddString("snapshot_path", str(snapshot_path_pattern))
        parameters["snapshot_parameters"].AddString("journal_path", str(self.test_directory / "journal.jrn"))

        def check(_) -> None:
            self.assertEqual(set(WRApp.CheckpointPattern(str(snapshot_path_pattern)).Glob()),
                             set([self.test_directory / f"step_{step}.h5" for step in range(3, 5+1)]))
        _Run(self, parameters, check)


    def test_CheckpointSelector(self) -> None:
        parameters = WRApp.CheckpointProcess.GetDefaultParameters()
        snapshot_path_pattern = self.test_directory / "step_<step>.h5"
        parameters["snapshot_parameters"].AddString("snapshot_path", str(snapshot_path_pattern))
        parameters["model_part_name"].SetString("test")
        parameters["snapshot_parameters"].AddString("journal_path", str(self.test_directory / "journal"))

        # Register a test checkpoint selector
        class TestCheckpointSelector(WRApp.CheckpointSelector):
            def __init__(self, *args): super().__init__()

            @classmethod
            def GetDefaultParameters(cls): return KratosMultiphysics.Parameters()

            def __call__(self, model):
                process_info = model.GetModelPart("test").ProcessInfo
                step = process_info[KratosMultiphysics.STEP]
                analysis_path = process_info[WRApp.ANALYSIS_PATH]
                checkpoint_id = WRApp.CheckpointID(step, analysis_path)
                return WRApp.CheckpointID(5, max(0, analysis_path - 1)) if checkpoint_id == WRApp.CheckpointID(15, analysis_path) else None

        selector_registry_path = "WRApplication.CheckpointSelector"
        if not WRApp.IsRegisteredPath(selector_registry_path):
            WRApp.RegisterClass(TestCheckpointSelector, selector_registry_path)

        # Set the newly registered checkpoint selector
        parameters["checkpoint_selector"]["type"].SetString(selector_registry_path)

        _Run(self, parameters)


    def test_InMemoryCheckpointWrite(self) -> None:
        """ @brief Checks checkpoint output with @ref SnapshotInMemory."""
        parameters = WRApp.CheckpointProcess.GetDefaultParameters()
        parameters["model_part_name"].SetString("test")
        parameters["write_predicate"]["type"].SetString("WRApplication.StepIntervalPredicate")
        parameters["write_predicate"]["parameters"] = KratosMultiphysics.Parameters(R"""[
            {"model_part_name" : "test"},
            {},
            {},
            {"interval" : [3, 5]}
        ]""")
        snapshot_path_pattern = self.test_directory / "step_<step>"
        parameters["snapshot_parameters"].AddString("snapshot_path", str(snapshot_path_pattern))
        parameters["snapshot_parameters"].AddString("journal_path", str(self.test_directory / "journal"))
        parameters["snapshot_type"].SetString("WRApplication.Snapshot.SnapshotInMemory")

        def check(_) -> None:
            self.assertEqual(set(WRApp.SnapshotInMemoryIO.Glob(str(self.test_directory / "step_*"))),
                             set([str(self.test_directory / f"step_{step}") for step in range(3, 5+1)]))
        _Run(self, parameters, check)


if __name__ == "__main__":
    WRApp.TestMain()
