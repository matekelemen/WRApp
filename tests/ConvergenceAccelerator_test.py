"""  @author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp
from MDPAGenerator import MDPAGenerator, GetMDPAPath

# --- STD Imports ---
import pathlib
import math


class ConvergenceAcceleratorTest(WRApp.TestCase):

    @property
    def mdpa_path(self) -> pathlib.Path:
        return GetMDPAPath("test_snapshot_2D")

    def test_MVQN(self) -> None:
        # Generate test model part
        generator = MDPAGenerator()
        model = KratosMultiphysics.Model()
        model_part = model.CreateModelPart("root")
        generator.Load(model_part, self.mdpa_path)

        # Get the variable to test the accelerator on
        # (pick an array3 variable)
        variable: WRApp.Typing.Variable = next((v for v in generator.historical_nodal_variables if isinstance(v, KratosMultiphysics.Array1DVariable3)), None)
        if variable is None:
            raise TypeError(f"No suitable Array1DVariable3 found in {generator.historical_nodal_variables}")

        # Construct an accelerator
        parameters = KratosMultiphysics.Parameters("""{
            "dataset" : {
                "type" : "WRApplication.Dataset.KratosDataset",
                "parameters" : {
                    "model_part_name" : "root",
                    "container_type" : "nodal_historical",
                    "variable_name" : ""
                }
            },
            "parameters" : {
                "type" : "mvqn"
            }
        }""")
        parameters["dataset"]["parameters"]["variable_name"].SetString(variable.Name())
        accelerator = WRApp.ConvergenceAccelerator(model, parameters)

        # Simulate a solution loop
        self.__SetNodalValues(model_part.Nodes, variable, 0)
        with accelerator as solution_step_accelerator:
            with solution_step_accelerator as nonlinear_solution_step_accelerator:
                for step in range(1, 11):
                    self.__SetNodalValues(model_part.Nodes, variable, step)
                    nonlinear_solution_step_accelerator.AddTerm()


    def __SetNodalValues(self,
                         nodes: KratosMultiphysics.NodesVector,
                         variable: WRApp.Typing.Variable,
                         step: int) -> None:
        for node in nodes:
            node.SetSolutionStepValue(variable, [node.X * (1.0 - math.exp(-step)),
                                                 node.Y * (1.0 - math.exp(-step)),
                                                 node.Z * (1.0 - math.exp(-step))])



if __name__ == "__main__":
    WRApp.TestMain()
