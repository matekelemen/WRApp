""" @author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics

# --- HDF5 Imports ---
import KratosMultiphysics.WRApplication as WRApp

# --- STD Imports ---
import pathlib
import itertools


class TestModelPartPattern(WRApp.TestCase):

    def setUp(self) -> None:
        """ @brief Create the following directory structure relative to the working directory:
            @code
            .
            └── test_path_pattern
                ├── valid_root
                    └── mdpa name_step_1_time_0.0.h5
                        └── mdpa name_step_1_time_10.h5
                    └── mdpa name_step_1_time_1.0.h5
                    └── mdpa name_step_1_time_1.h5
                    └── mdpa name_step_1_time_1.1.h5
                    └── mdpa name_step_2_time_1.0.h5
                    └── mdpa name_step_3_time_0.5.h5
                    └── mdpa name_step_3_time_2.h5
                    └── mdpa name_step_3_time_03.h5
                    └── mdpa name_step_3_time_004.0.h5
                    └── mdpa_name_step_1_time_1.h5
                    └── m_dpa_name_step_1_time_1.h5
                    └── mdpa name_step_04_time_1.h5
                    └── mdpa name_step_04_time_2.hdf5
                    └── ir.relevant
                └── invalid_root
                    └── mdpa name_step_1_time_0.0.h5
                        └── mdpa name_step_1_time_10.h5
                    └── mdpa name_step_1_time_1.0.h5
                    └── mdpa name_step_1_time_1.h5
                    └── mdpa name_step_1_time_1.1.h5
                    └── mdpa name_step_2_time_1.0.h5
                    └── mdpa name_step_3_time_0.5.h5
                    └── mdpa name_step_3_time_2.h5
                    └── mdpa name_step_3_time_03.h5
                    └── mdpa name_step_3_time_004.0.h5
                    └── mdpa_name_step_1_time_1.h5
                    └── m_dpa_name_step_1_time_1.h5
                    └── mdpa name_step_04_time_1.h5
                    └── mdpa name_step_04_time_2.hdf5
                    └── ir.relevant
                └── step_1
                    └── mdpa name_time_1.h5
                └── step_2
                    └── mdpa name_time_0.h5
                @endcode
        """
        KratosMultiphysics.kratos_utilities.DeleteDirectoryIfExisting("test_path_pattern")
        mkdir_arguments = {"exist_ok" : False, "parents" : True}
        self.test_root = pathlib.Path().cwd() / "test_path_pattern"
        self.valid_root = self.test_root / "valid_root"
        self.invalid_root = self.test_root / "invalid_root"

        file_names = [
            "mdpa name_step_1_time_1.0.h5",
            "mdpa name_step_1_time_1.h5",
            "mdpa name_step_1_time_1.1.h5",
            "mdpa name_step_2_time_1.0.h5",
            "mdpa name_step_3_time_0.5.h5",
            "mdpa name_step_3_time_2.h5",
            "mdpa name_step_3_time_03.h5",
            "mdpa name_step_3_time_004.0.h5",
            "mdpa_name_step_1_time_1.h5",
            "m_dpa_name_step_1_time_1.h5",
            "mdpa name_step_04_time_1.h5",
            "mdpa name_step_04_time_2.hdf5",
            "ir.relevant"
        ]

        for directory in (self.test_root, self.valid_root, self.invalid_root):
            (directory / "mdpa name_step_1_time_0.0.h5").mkdir(**mkdir_arguments)
            (directory / "mdpa name_step_1_time_0.0.h5" / "mdpa name_step_1_time_10.h5").touch(exist_ok=False)

        for file_name in file_names:
            (self.valid_root / file_name).touch(exist_ok=False)
            (self.invalid_root / file_name).touch(exist_ok=False)

        (self.test_root / "step_1").mkdir(**mkdir_arguments)
        (self.test_root / "step_1" / "mdpa name_time_1.h5").touch(exist_ok=False)
        (self.test_root / "step_2").mkdir(**mkdir_arguments)
        (self.test_root / "step_2" / "mdpa name_time_0.h5").touch(exist_ok=False)

    def tearDown(self) -> None:
        """Remove ./test_path_pattern"""
        KratosMultiphysics.kratos_utilities.DeleteDirectoryIfExisting("test_path_pattern")

    def test_IsAMatch(self) -> None:
        pattern_string = "mdpa_name_<model_part_name>_step_<step>_time_<time>_suffix"
        pattern = WRApp.ModelPartPattern(pattern_string)

        valid_strings = [
            "mdpa_name_NAME_step_1_time_1.0_suffix",
            "mdpa_name_N_step_1_time_1.0_suffix",
            "mdpa_name_NAME_step_123456789_time_1.0_suffix",
            "mdpa_name_NAME_step_1_time_1_suffix",
            "mdpa_name_NAME_step_1_time_-1.0_suffix",
            "mdpa_name_NAME_step_1_time_-1_suffix",
            "mdpa_name_NAME_step_1_time_0.123456789_suffix"
        ]

        invalid_strings = [
            "mdpa_name_NAME_step_01_time_1.0_suffix",
            "mdpa_name_NAME_step_0101_time_1.0_suffix",
            "mdpa_name__step_1_time_1.0_suffix",
            "mdpa_name_NAME_step__time_1.0_suffix",
            "mdpa_name_NAME_step_1O_time_1.0_suffix",
            "mdpa_name_NAME_step_1a1_time_1.0_suffix",
            "mdpa_name_NAME_step_1_time__suffix",
            "mdpa_name_NAME_step_1_time_1.O_suffix",
            "mdpa_name_NAME_step_1_time_1.0_suffiy",
            "Mdpa_name_NAME_step_1_time_1.0_suffix"
        ]

        for string in valid_strings:
            self.assertTrue(pattern.IsAMatch(string), msg = "{} should match but it doesn't".format(string))

        for string in invalid_strings:
            self.assertFalse(pattern.IsAMatch(string), msg = "{} shouldn't match but it does".format(string))

    def test_Match(self) -> None:
        pattern_string = "<model_part_name>/name_<model_part_name>_step_<step>_time_<time>suffix"
        pattern = WRApp.ModelPartPattern(pattern_string)

        placeholders = ("<model_part_name>", "<step>", "<time>")
        values = [
            dict(zip(placeholders, ("mdpa name", "1", "1.0"))),
            dict(zip(placeholders, ("mdpa name", "10", "1"))),
            dict(zip(placeholders, (r'()[]\\"-+_*' + "'", "90", "0.010")))
        ]

        for dictionary in values:
            string = pattern_string
            for key, value in dictionary.items():
                string = string.replace(key, value)
            matches = pattern.Match(string)

            for key, value in dictionary.items():
                self.assertIn(key, matches)
                self.assertTrue(matches[key])
                for match_value in matches[key]:
                    self.assertEqual(match_value, value)

            self.assertEqual(len(matches["<model_part_name>"]), 2)

    def test_Apply(self) -> None:
        pattern = "prefix/<step>_<model_part_name>_<time><not_a_placeholder>/<time>.suffix"
        model_part_pattern = WRApp.ModelPartPattern(pattern)
        model_part_names = ("mdpa name", r"""\/=()@$&^""")
        times = (-5.0, -5, 0.0, 1.0, 30, "10.0101E-1")
        steps = (0, 1, 1009)

        model_part = KratosMultiphysics.Model().CreateModelPart("_")

        for model_part_name, time, step in itertools.product(model_part_names, times, steps):
            placeholder_map = {
                "<model_part_name>" : model_part_name,
                "<time>" : str(time),
                "<step>" : str(step)
            }

            reference = pattern
            for placeholder, value in placeholder_map.items():
                reference = reference.replace(placeholder, value)

            # Test apply from a map
            applied_string = model_part_pattern.Apply(placeholder_map)
            self.assertEqual(applied_string,
                             reference)

            # Test apply from a model part
            model_part.Name = model_part_name
            model_part.ProcessInfo[KratosMultiphysics.TIME] = float(time)
            model_part.ProcessInfo[KratosMultiphysics.STEP] = step
            applied_string = model_part_pattern.Apply(model_part)
            # Testing the output string directly doesn't make sense
            # until formatting options are implemented.
            #self.assertEqual(model_part_pattern.Apply(model_part),
            #                 reference)

    def test_Glob(self) -> None:
        valid_paths = {
            self.valid_root / "mdpa name_step_1_time_0.0.h5",
            self.valid_root / "mdpa name_step_1_time_1.h5",
            self.valid_root / "mdpa name_step_1_time_1.0.h5",
            self.valid_root / "mdpa name_step_1_time_1.1.h5",
            self.valid_root / "mdpa name_step_2_time_1.0.h5",
            self.valid_root / "mdpa name_step_3_time_0.5.h5",
            self.valid_root / "mdpa name_step_3_time_2.h5",
        }

        invalid_paths = {
            self.valid_root / "mdpa name_step_3_time_03.h5",
            self.valid_root / "mdpa name_step_3_time_004.0.h5",
            self.valid_root / "mdpa name_step_04_time_1.h5",
            self.valid_root / "mdpa_name_step_1_time_1.h5",
            self.valid_root / "m_dpa_name_step_1_time_1.h5",
            self.valid_root / "mdpa name_step_04_time_2.hdf5",
            self.valid_root / "ir.relevant",
            self.invalid_root / "mdpa name_step_1_time_1.0.h5",
            self.invalid_root / "mdpa name_step_1_time_1.h5",
            self.invalid_root / "mdpa name_step_1_time_1.1.h5",
            self.invalid_root / "mdpa name_step_2_time_1.0.h5",
            self.invalid_root / "mdpa name_step_3_time_0.5.h5",
            self.invalid_root / "mdpa name_step_3_time_2.h5",
            self.invalid_root / "mdpa name_step_3_time_03.h5",
            self.invalid_root / "mdpa name_step_3_time_004.0.h5",
            self.invalid_root / "ir.relevant",
            self.test_root / "mdpa name_step_1_time_0.0.h5" / "mdpa name_step_1_time_0.0.h5"
        }

        pattern_string = "test_path_pattern/valid_root/<model_part_name>_step_<step>_time_<time>.h5"

        # Base pattern (all placeholders)
        pattern = WRApp.ModelPartPattern(pattern_string)
        paths = [pathlib.Path(path) for path in pattern.Glob()]
        for path in valid_paths:
            self.assertIn(path, paths, msg = path)

        extra = {
            self.valid_root / "mdpa_name_step_1_time_1.h5",
            self.valid_root / "m_dpa_name_step_1_time_1.h5"
        }
        self.assertEqual(len(paths), len(valid_paths) + len(extra))
        for path in valid_paths | extra:
            self.assertIn(path, paths, msg = path)
        for path in invalid_paths - extra:
            self.assertNotIn(path, paths, msg = path)

        # Partial pattern (<model_part_name> replaced)
        pattern = WRApp.ModelPartPattern(pattern_string.replace("<model_part_name>", "mdpa name"))
        paths = [pathlib.Path(path) for path in pattern.Glob()]
        self.assertEqual(len(paths), len(valid_paths))
        for path in valid_paths:
            self.assertIn(path, paths, msg = path)
        for path in invalid_paths:
            self.assertNotIn(path, paths, msg = path)


class TestCheckpointPattern(WRApp.TestCase):

    def setUp(self) -> None:
        KratosMultiphysics.kratos_utilities.DeleteDirectoryIfExisting(str(self.test_files_directory))
        for file_path in self.valid_paths + self.invalid_paths:
            file_path.parent.mkdir(exist_ok = True, parents = True)
            file_path.touch(exist_ok = False)

    def tearDown(self) -> None:
        KratosMultiphysics.kratos_utilities.DeleteDirectoryIfExisting(str(self.test_files_directory))

    @property
    def test_files_directory(self) -> pathlib.Path:
        return pathlib.Path("test_path_pattern")

    @property
    def valid_paths(self) -> list:
        return [self.test_files_directory / "mdpa_name_step_1_time_2_path_id_3.h5",
                self.test_files_directory / "mdpa_name_step_1_time_2_path_id_4.h5"]

    @property
    def invalid_paths(self) -> list:
        return [self.test_files_directory / "mdpa_name_step_1_time_2_path_id_-3.h5",
                self.test_files_directory / "mdpa_name_step_1_time_2_path_id_3.hdf5",
                self.test_files_directory / "in.valid",
                self.test_files_directory / "mdpa_name_step_1_time_2_path_id_5.h5" / "mdpa_name_step_1_time_2_path_id_5.h5"]

    def test_Glob(self) -> None:
        pattern = self.test_files_directory / "<model_part_name>_step_<step>_time_<time>_path_id_<path_id>.h5"

        # Relative glob
        checkpoint_pattern = WRApp.CheckpointPattern(str(pattern))
        globbed_paths = checkpoint_pattern.Glob()
        self.CheckGlobbedResults(globbed_paths)

        # Absolute glob
        checkpoint_pattern = WRApp.CheckpointPattern(str(pattern.absolute()))
        globbed_paths = checkpoint_pattern.Glob()
        self.CheckGlobbedResults(globbed_paths)

    def CheckGlobbedResults(self, paths: list) -> None:
        for path in [p.absolute() for p in self.valid_paths]:
            self.assertIn(path, paths)
        for path in [p.absolute() for p in self.invalid_paths]:
            self.assertNotIn(path, paths)

if __name__ == "__main__":
    WRApp.TestMain()