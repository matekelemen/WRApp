"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics
import KratosMultiphysics.KratosUnittest as KratosUnittest
from KratosMultiphysics.kratos_utilities import DeleteDirectoryIfExisting
from KratosMultiphysics.testing.utilities import ReadModelPart

# --- WRApp Imports ---
import KratosMultiphysics.WRApp as WRApp
import KratosMultiphysics.WRApp.checkpoint.Snapshot as Snapshots

# --- STD Imports ---
import pathlib


def GetMDPAPath() -> pathlib.Path:
    script_directory = pathlib.Path(__file__).absolute().parent
    return script_directory / "data" / "test_snapshot"


def SetModelPartData(model_part: KratosMultiphysics.ModelPart, step: int = 0, path: int = 0, time: float = 0.0) -> None:
    model_part.ProcessInfo[KratosMultiphysics.STEP] = step
    model_part.ProcessInfo[WRApp.ANALYSIS_PATH] = path
    model_part.ProcessInfo[KratosMultiphysics.TIME] = time

    for node in model_part.Nodes:
        node.SetSolutionStepValue(KratosMultiphysics.PRESSURE, path + step * time * (node.Id << 1)) # historical
        node[KratosMultiphysics.NODAL_H] = path + step * time * node.Id # non-historical

    for element in model_part.Elements:
        element[KratosMultiphysics.ELEMENT_H] = -(path + step * time * element.Id)

    for condition in model_part.Conditions:
        condition[KratosMultiphysics.ELEMENT_H] = -2 * (path + step * time * condition.Id)


def MakeModelPart(model: KratosMultiphysics.Model, name: str = "test") -> KratosMultiphysics.ModelPart:
    model_part = model.CreateModelPart(name)
    model_part.ProcessInfo[KratosMultiphysics.STEP] = 0
    model_part.ProcessInfo[KratosMultiphysics.TIME] = 0.0
    model_part.ProcessInfo[WRApp.ANALYSIS_PATH] = 0
    model_part.ProcessInfo[KratosMultiphysics.DOMAIN_SIZE] = 2
    model_part.AddNodalSolutionStepVariable(KratosMultiphysics.PRESSURE)
    ReadModelPart(str(GetMDPAPath()), model_part)
    SetModelPartData(model_part)
    return model_part


def MakeModel() -> "tuple[KratosMultiphysics.Model, KratosMultiphysics.ModelPart]":
    model = KratosMultiphysics.Model()
    return model, MakeModelPart(model)


def FlipFlags(container) -> None:
    for item in container:
        item.Set(item, False)


def CompareModelParts(source_model_part: KratosMultiphysics.ModelPart,
                      target_model_part: KratosMultiphysics.ModelPart,
                      test_case: KratosUnittest.TestCase) -> None:
    # Compare nodes
    test_case.assertEqual(len(source_model_part.Nodes), len(target_model_part.Nodes))
    for source_node, target_node in zip(source_model_part.Nodes, target_model_part.Nodes):
        # Check non-historical variable
        test_case.assertAlmostEqual(source_node[KratosMultiphysics.NODAL_H], target_node[KratosMultiphysics.NODAL_H])

        # Check historical variable
        test_case.assertAlmostEqual(source_node.GetSolutionStepValue(KratosMultiphysics.PRESSURE), target_node.GetSolutionStepValue(KratosMultiphysics.PRESSURE))

        # Check properties
        for property_name in ["X", "Y", "Z", "X0", "Y0", "Z0", "Id"]:
            test_case.assertAlmostEqual(getattr(source_node, property_name), getattr(target_node, property_name))
            pass

        # Check flags
        test_case.assertTrue(source_node.Is(target_node))


    # Compare elements
    test_case.assertEqual(len(source_model_part.Elements), len(target_model_part.Elements))
    for source_element, target_element in zip(source_model_part.Elements, target_model_part.Elements):
        # Check nodes
        for source_node, target_node in zip(source_element.GetNodes(), target_element.GetNodes()):
            test_case.assertTrue(source_node.Id, target_node.Id)
            pass

        # Check flags
        test_case.assertTrue(source_element.Is(target_element))

        ##! @todo Compare element variables (@matekelemen)

    # Compare conditions
    test_case.assertEqual(len(source_model_part.Conditions), len(target_model_part.Conditions))
    for source_condition, target_condition in zip(source_model_part.Conditions, target_model_part.Conditions):
        # Check nodes
        for source_node, target_node in zip(source_condition.GetNodes(), target_condition.GetNodes()):
            test_case.assertTrue(source_node.Id, target_node.Id)
            pass

        # Check flags
        test_case.assertTrue(source_condition.Is(target_condition))

        ##! @todo Compare condition variables (@matekelemen)


class TestSnapshotOnDisk(KratosUnittest.TestCase):

    @property
    def test_directory(self) -> pathlib.Path:
        return pathlib.Path("test_snapshot_on_disk")

    @property
    def file_path(self) -> pathlib.Path:
        return self.test_directory / "checkpoints" / "snapshot.h5"

    def setUp(self) -> None:
        DeleteDirectoryIfExisting(str(self.test_directory))
        KratosMultiphysics.Testing.GetDefaultDataCommunicator().Barrier()
        (self.test_directory / "checkpoints").mkdir(parents = True, exist_ok = True)

    def tearDown(self) -> None:
        DeleteDirectoryIfExisting(str(self.test_directory))
        KratosMultiphysics.Testing.GetDefaultDataCommunicator().Barrier()

    def test_ReadWrite(self) -> None:
        input_parameters = Snapshots.DefaultSnapshotInput.GetDefaultParameters()
        output_parameters = Snapshots.DefaultSnapshotOutput.GetDefaultParameters()

        input_parameters["io_settings"]["file_name"].SetString(str(self.file_path))
        output_parameters["io_settings"]["file_name"].SetString(str(self.file_path))
        for parameters in (input_parameters, output_parameters):
            parameters["io_settings"]["file_name"].SetString(str(parameters["io_settings"]["file_name"].GetString()))

        model, source_model_part = MakeModel()
        SetModelPartData(source_model_part, step = 2, path = 3, time = 1.5)

        # Check initialized source model part ProcessInfo
        self.assertEqual(source_model_part.ProcessInfo[KratosMultiphysics.STEP], 2)
        self.assertEqual(source_model_part.ProcessInfo[WRApp.ANALYSIS_PATH], 3)
        self.assertEqual(source_model_part.ProcessInfo[KratosMultiphysics.TIME], 1.5)

        snapshot = Snapshots.SnapshotOnDisk(
            source_model_part.ProcessInfo[KratosMultiphysics.STEP],
            source_model_part.ProcessInfo[WRApp.ANALYSIS_PATH],
            input_parameters,
            output_parameters)
        snapshot.Write(source_model_part)
        KratosMultiphysics.Testing.GetDefaultDataCommunicator().Barrier()

        # Check initialized source model part ProcessInfo (unchanged)
        self.assertEqual(source_model_part.ProcessInfo[KratosMultiphysics.STEP], 2)
        self.assertEqual(source_model_part.ProcessInfo[WRApp.ANALYSIS_PATH], 3)
        self.assertEqual(source_model_part.ProcessInfo[KratosMultiphysics.TIME], 1.5)

        # Create target model part with different data
        target_model_part = MakeModelPart(model, "read")
        SetModelPartData(target_model_part, step = 10, path = 2, time = 3.5)
        FlipFlags(target_model_part.Nodes)
        FlipFlags(target_model_part.Elements)
        FlipFlags(target_model_part.Conditions)
        ##! @todo Modify element and condition variables in target_model_part

        # Check initialized target model part ProcessInfo
        self.assertEqual(target_model_part.ProcessInfo[KratosMultiphysics.STEP], 10)
        self.assertEqual(target_model_part.ProcessInfo[WRApp.ANALYSIS_PATH], 2)
        self.assertEqual(target_model_part.ProcessInfo[KratosMultiphysics.TIME], 3.5)

        snapshot.Load(target_model_part)

        # Check loaded target model part ProcessInfo
        self.assertEqual(target_model_part.ProcessInfo[KratosMultiphysics.STEP], 2)
        self.assertEqual(target_model_part.ProcessInfo[WRApp.ANALYSIS_PATH], 3)
        self.assertEqual(target_model_part.ProcessInfo[KratosMultiphysics.TIME], 1.5)

        CompareModelParts(source_model_part, target_model_part, self)


if __name__ == "__main__":
    KratosUnittest.main()
