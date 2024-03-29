"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics
from KratosMultiphysics.kratos_utilities import DeleteDirectoryIfExisting
from KratosMultiphysics.testing.utilities import ReadModelPart

# --- WRApplication Imports ---
import KratosMultiphysics.WRApplication as WRApp
from KratosMultiphysics.WRApplication.MPIUtils import MPIUtils
from MDPAGenerator import MDPAGenerator, GetMDPAPath

# --- STD Imports ---
import pathlib


def SetModelPartData(model_part: KratosMultiphysics.ModelPart,
                     step: int = 0,
                     path: int = 0,
                     time: float = 0.0) -> None:
    generator = MDPAGenerator()
    model_part.ProcessInfo[KratosMultiphysics.STEP] = step
    model_part.ProcessInfo[WRApp.ANALYSIS_PATH] = path
    model_part.ProcessInfo[KratosMultiphysics.TIME] = time

    for node in model_part.Nodes:
        for i_variable, variable in enumerate(generator.historical_nodal_variables):
            node.SetSolutionStepValue(variable,
                                      generator.SetAll(variable, i_variable + path + step * time * (node.Id << 1))) # historical
        for i_variable, variable in enumerate(generator.nodal_variables):
            node[variable] = generator.SetAll(variable, path + step * time * node.Id) # non-historical

    for element in model_part.Elements:
        for i_variable, variable in enumerate(generator.element_variables):
            element[variable] = generator.SetAll(variable, i_variable - (path + step * time * element.Id))

    for condition in model_part.Conditions:
        for i_variable, variable in enumerate(generator.condition_variables):
            condition[variable] = generator.SetAll(variable, i_variable - 2 * (path + step * time * condition.Id))


def MakeModelPart(model: KratosMultiphysics.Model,
                  name: str = "test",
                  buffer_size: int = 1,
                  mdpa_name: str = "test_snapshot_2D") -> KratosMultiphysics.ModelPart:
    generator = MDPAGenerator()
    model_part = model.CreateModelPart(name)
    model_part.SetBufferSize(buffer_size)
    model_part.ProcessInfo[KratosMultiphysics.STEP] = 0
    model_part.ProcessInfo[KratosMultiphysics.TIME] = 0.0
    model_part.ProcessInfo[WRApp.ANALYSIS_PATH] = 0
    model_part.ProcessInfo[KratosMultiphysics.DOMAIN_SIZE] = 2
    generator.Load(model_part, GetMDPAPath(mdpa_name))
    SetModelPartData(model_part)
    return model_part


def MakeModel(buffer_size: int = 1,
              mdpa_name: str = "test_snapshot_2D") -> "tuple[KratosMultiphysics.Model, KratosMultiphysics.ModelPart]":
    model = KratosMultiphysics.Model()
    return model, MakeModelPart(model, buffer_size = buffer_size, mdpa_name = mdpa_name)


def FlipFlags(container) -> None:
    for item in container:
        item.Set(item, False)


def CompareModelParts(source_model_part: KratosMultiphysics.ModelPart,
                      target_model_part: KratosMultiphysics.ModelPart,
                      test_case: WRApp.TestCase,
                      generator: MDPAGenerator = MDPAGenerator()) -> None:
    test_case.assertEqual(source_model_part.GetBufferSize(), target_model_part.GetBufferSize())

    # Compare nodes
    test_case.assertEqual(len(source_model_part.Nodes), len(target_model_part.Nodes))
    for source_node, target_node in zip(source_model_part.Nodes, target_model_part.Nodes):
        # Check non-historical variable
        for variable in generator.nodal_variables:
            test_case.assertAlmostEqual(source_node[variable],
                                        target_node[variable],
                                        msg = variable.Name())

        # Check properties
        for property_name in ["X", "Y", "Z", "X0", "Y0", "Z0", "Id"]:
            test_case.assertAlmostEqual(getattr(source_node, property_name), getattr(target_node, property_name))

            # Check flags
            test_case.assertTrue(source_node.Is(target_node))

        # Check historical variables
        for buffer_index in range(source_model_part.GetBufferSize()):
            for variable in generator.historical_nodal_variables:
                test_case.assertTrue(source_node.SolutionStepsDataHas(variable))
                test_case.assertTrue(target_node.SolutionStepsDataHas(variable))
                test_case.assertAlmostEqual(source_node.GetSolutionStepValue(variable, buffer_index),
                                            target_node.GetSolutionStepValue(variable, buffer_index),
                                            msg = f"{variable.Name()} in buffer #{buffer_index} of {[v.Name() for v in generator.historical_nodal_variables]}")

    # Compare elements
    test_case.assertEqual(len(source_model_part.Elements), len(target_model_part.Elements))
    for source_element, target_element in zip(source_model_part.Elements, target_model_part.Elements):
        # Check nodes
        for source_node, target_node in zip(source_element.GetNodes(), target_element.GetNodes()):
            test_case.assertTrue(source_node.Id, target_node.Id)

        # Check flags
        test_case.assertTrue(source_element.Is(target_element))

        # Compare variables
        for variable in generator.element_variables:
            test_case.assertTrue(source_element.Has(variable))
            test_case.assertTrue(target_element.Has(variable))
            test_case.assertAlmostEqual(source_element[variable],
                                        target_element[variable],
                                        msg = variable.Name())

    # Compare conditions
    test_case.assertEqual(len(source_model_part.Conditions), len(target_model_part.Conditions))
    for source_condition, target_condition in zip(source_model_part.Conditions, target_model_part.Conditions):
        # Check nodes
        for source_node, target_node in zip(source_condition.GetNodes(), target_condition.GetNodes()):
            test_case.assertTrue(source_node.Id, target_node.Id)

        # Check flags
        test_case.assertTrue(source_condition.Is(target_condition))

        # Compare variables
        for variable in generator.condition_variables:
            test_case.assertTrue(source_condition.Has(variable), msg = variable.Name())
            test_case.assertTrue(target_condition.Has(variable), msg = variable.Name())
            test_case.assertAlmostEqual(source_condition[variable],
                                        target_condition[variable],
                                        msg = variable.Name())

    # Compare process infos
    test_case.assertEqual(len(source_model_part.ProcessInfo), len(target_model_part.ProcessInfo))
    for variable in generator.process_info_variables:
        test_case.assertTrue(source_model_part.ProcessInfo.Has(variable))
        test_case.assertTrue(target_model_part.ProcessInfo.Has(variable))
        test_case.assertAlmostEqual(source_model_part.ProcessInfo[variable], target_model_part.ProcessInfo[variable])


class TestHDF5Snapshot(WRApp.TestCase):

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
        #DeleteDirectoryIfExisting(str(self.test_directory))
        KratosMultiphysics.Testing.GetDefaultDataCommunicator().Barrier()

    def test_ReadWrite(self) -> None:
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

        model, source_model_part = MakeModel(mdpa_name = mdpa_name)
        SetModelPartData(source_model_part, step = 2, path = 3, time = 1.5)

        parameters = WRApp.HDF5Snapshot.GetDefaultParameters()
        for io in (parameters["input_parameters"], parameters["output_parameters"]):
            io["io_settings"]["file_name"].SetString(str(self.file_path))
            io["nodal_historical_variables"].SetStringArray([variable.Name() for variable in generator.historical_nodal_variables])
            io["nodal_variables"].SetStringArray([variable.Name() for variable in generator.nodal_variables])
            io["nodal_flags"].SetStringArray(MPIUtils.ExtractNodalFlagNames(source_model_part))
            io["element_variables"].SetStringArray([variable.Name() for variable in generator.element_variables])
            io["element_flags"].SetStringArray(MPIUtils.ExtractElementFlagNames(source_model_part))
            io["condition_variables"].SetStringArray([variable.Name() for variable in generator.condition_variables])
            io["condition_flags"].SetStringArray(MPIUtils.ExtractConditionFlagNames(source_model_part))

        # Check initialized source model part ProcessInfo
        self.assertEqual(source_model_part.ProcessInfo[KratosMultiphysics.STEP], 2)
        self.assertEqual(source_model_part.ProcessInfo[WRApp.ANALYSIS_PATH], 3)
        self.assertEqual(source_model_part.ProcessInfo[KratosMultiphysics.TIME], 1.5)

        snapshot = WRApp.HDF5Snapshot(WRApp.CheckpointID(source_model_part.ProcessInfo[KratosMultiphysics.STEP],
                                                         source_model_part.ProcessInfo[WRApp.ANALYSIS_PATH]),
                                      parameters)
        snapshot.Write(source_model_part)

        # Check initialized source model part ProcessInfo (unchanged)
        self.assertEqual(source_model_part.ProcessInfo[KratosMultiphysics.STEP], 2)
        self.assertEqual(source_model_part.ProcessInfo[WRApp.ANALYSIS_PATH], 3)
        self.assertEqual(source_model_part.ProcessInfo[KratosMultiphysics.TIME], 1.5)

        # Create target model part with different data
        target_model_part = MakeModelPart(model, "target", mdpa_name = mdpa_name)
        SetModelPartData(target_model_part, step = 10, path = 2, time = 3.5)
        FlipFlags(target_model_part.Nodes)
        FlipFlags(target_model_part.Elements)
        FlipFlags(target_model_part.Conditions)

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


class TestSnapshotInMemory(WRApp.TestCase):

    def test_ReadWrite(self) -> None:
        for mdpa_stub in ("simple", "2D"):
            with self.subTest(mdpa_stub):
                try:
                    self.setUp()
                    self.RunModel(mdpa_stub)
                finally:
                    self.tearDown()


    def tearDown(self) -> None:
        WRApp.SnapshotInMemoryOutput.Clear()


    def RunModel(self, mdpa_stub: str) -> None:
        mdpa_name = f"test_snapshot_{mdpa_stub}"
        generator = MDPAGenerator()

        model, source_model_part = MakeModel(mdpa_name = mdpa_name)
        SetModelPartData(source_model_part, step = 2, path = 3, time = 1.5)

        parameters = WRApp.SnapshotInMemory.GetDefaultParameters()
        for io in (parameters["input_parameters"], parameters["output_parameters"]):
            io["file_name"].SetString("/this/is/not/really/a/path")
            io["nodal_historical_variables"].SetStringArray([variable.Name() for variable in generator.historical_nodal_variables])
            io["nodal_variables"].SetStringArray([variable.Name() for variable in generator.nodal_variables])
            io["nodal_flags"].SetStringArray(MPIUtils.ExtractNodalFlagNames(source_model_part))
            io["element_variables"].SetStringArray([variable.Name() for variable in generator.element_variables])
            io["element_flags"].SetStringArray(MPIUtils.ExtractElementFlagNames(source_model_part))
            io["condition_variables"].SetStringArray([variable.Name() for variable in generator.condition_variables])
            io["condition_flags"].SetStringArray(MPIUtils.ExtractConditionFlagNames(source_model_part))

        # Check initialized source model part ProcessInfo
        self.assertEqual(source_model_part.ProcessInfo[KratosMultiphysics.STEP], 2)
        self.assertEqual(source_model_part.ProcessInfo[WRApp.ANALYSIS_PATH], 3)
        self.assertEqual(source_model_part.ProcessInfo[KratosMultiphysics.TIME], 1.5)

        snapshot = WRApp.SnapshotInMemory(WRApp.CheckpointID(source_model_part.ProcessInfo[KratosMultiphysics.STEP],
                                                             source_model_part.ProcessInfo[WRApp.ANALYSIS_PATH]),
                                          parameters)
        snapshot.Write(source_model_part)

        # Check initialized source model part ProcessInfo (unchanged)
        self.assertEqual(source_model_part.ProcessInfo[KratosMultiphysics.STEP], 2)
        self.assertEqual(source_model_part.ProcessInfo[WRApp.ANALYSIS_PATH], 3)
        self.assertEqual(source_model_part.ProcessInfo[KratosMultiphysics.TIME], 1.5)

        # Create target model part with different data
        target_model_part = MakeModelPart(model, "target", mdpa_name = mdpa_name)
        SetModelPartData(target_model_part, step = 10, path = 2, time = 3.5)
        FlipFlags(target_model_part.Nodes)
        FlipFlags(target_model_part.Elements)
        FlipFlags(target_model_part.Conditions)

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
    WRApp.TestMain()
