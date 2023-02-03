"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics
from KratosMultiphysics.testing.utilities import ReadModelPart

# --- STD Imports ---
import typing
import pathlib


class MDPAGenerator:
    """@brief Convenience class for generating @ref ModelPart s for testing."""

    @property
    def historical_nodal_variables(self) -> "list[typing.Any]":
        return [
            #KratosMultiphysics.COMPUTE_DYNAMIC_TANGENT,     # bool
            KratosMultiphysics.REFINEMENT_LEVEL,            # int
            KratosMultiphysics.DELTA_TIME,                  # double
            KratosMultiphysics.ROTATION,                    # double array
            #KratosMultiphysics.DEFORMATION_GRADIENT         # double matrix
        ]


    @property
    def nodal_variables(self) -> "list[typing.Any]":
        return [
            #KratosMultiphysics.IS_RESTARTED,                # bool
            KratosMultiphysics.RIGID_BODY_ID,               # int
            KratosMultiphysics.INTERVAL_END_TIME,           # double
            KratosMultiphysics.MOMENT,                      # double vector
            KratosMultiphysics.LOCAL_INERTIA_TENSOR         # double matrix
        ]


    @property
    def element_variables(self) -> "list[typing.Any]":
        return [
            #KratosMultiphysics.IS_RESTARTED,                # bool
            KratosMultiphysics.LOAD_RESTART,                # int
            KratosMultiphysics.START_TIME,                  # double
            KratosMultiphysics.DELTA_ROTATION,              # double array
            KratosMultiphysics.PK2_STRESS_TENSOR            # double matrix
        ]


    @property
    def condition_variables(self) -> "list[typing.Any]":
        return [
            #KratosMultiphysics.COMPUTE_LUMPED_MASS_MATRIX,  # bool
            KratosMultiphysics.FIRST_TIME_STEP,             # int
            KratosMultiphysics.END_TIME,                    # double
            KratosMultiphysics.REACTION_MOMENT,             # double array
            KratosMultiphysics.CAUCHY_STRESS_TENSOR         # double matrix
        ]


    def Write(self,
              model_part: KratosMultiphysics.ModelPart,
              file_path: pathlib.Path) -> None:
        KratosMultiphysics.ModelPartIO(file_path, KratosMultiphysics.IO.WRITE).WriteModelPart(model_part)


    def Load(self,
             model_part: KratosMultiphysics.ModelPart,
             file_path: pathlib.Path) -> None:
        for variable in self.historical_nodal_variables:
            model_part.AddNodalSolutionStepVariable(variable)
        ReadModelPart(str(file_path), model_part)


    def MakeRootModelPart(self,
                          model: KratosMultiphysics.Model,
                          name: str = "root",
                          buffer_size: int = 3,
                          number_of_subdivisions: int = 5) -> KratosMultiphysics.ModelPart:
        """@brief Create a @ref ModelPart on a unit square."""
        model_part = model.CreateModelPart(name)
        model_part.ProcessInfo[KratosMultiphysics.DOMAIN_SIZE] = 3
        model_part.SetBufferSize(buffer_size)

        # Add historical variables
        for variable in self.historical_nodal_variables:
            model_part.AddNodalSolutionStepVariable(variable)

        # Create mesh
        root_element = KratosMultiphysics.Quadrilateral2D4(
            KratosMultiphysics.Node(1, 0.0, 0.0, 0.0),
            KratosMultiphysics.Node(2, 0.0, 1.0, 0.0),
            KratosMultiphysics.Node(3, 1.0, 1.0, 0.0),
            KratosMultiphysics.Node(4, 1.0, 0.0, 0.0)
        )
        mesh_parameters = KratosMultiphysics.Parameters("""{
            "number_of_divisions" : -1,
            "element_name" : "Element2D3N",
            "create_skin_sub_model_part" : true,
            "condition_name" : "LineCondition"
        }""")
        mesh_parameters["number_of_divisions"].SetInt(number_of_subdivisions)
        KratosMultiphysics.StructuredMeshGeneratorProcess(root_element,
                                                          model_part,
                                                          mesh_parameters).Execute()

        # Add nodal variables to **all** nodes
        for node in model_part.Nodes:
            for variable in self.nodal_variables:
                node[variable] = self.SetAll(variable, 0)

        # Add element variables to **all** elements
        for element in model_part.Elements:
            for variable in self.element_variables:
                element[variable] = self.SetAll(variable, 0)

        # Add condition variables to **all** conditions
        for condition in model_part.Conditions:
            for variable in self.condition_variables:
                condition[variable] = self.SetAll(variable, 0)

        return model_part


    def MakeSubModelParts(self, root_model_part: KratosMultiphysics.ModelPart) -> "list[KratosMultiphysics.ModelPart]":
        """@brief Partition the input @ref ModelPart into top and bottom thirds.
        @detail - top: nodes with y-coordinates > 2/3
                - bottom: nodes with y-coordinates < 1/3"""
        bottom_model_part = root_model_part.CreateSubModelPart("bottom")
        top_model_part = root_model_part.CreateSubModelPart("top")
        boundaries = (1/3.0, 2/3.0)
        for node in root_model_part.Nodes:
            if node.Y < boundaries[0]:
                bottom_model_part.AddNode(node, 0)
            elif boundaries[1] < node.Y:
                top_model_part.AddNode(node, 0)
        return [bottom_model_part, top_model_part]


    @staticmethod
    def SetAll(variable: typing.Any, value: typing.Any) -> typing.Any:
        """@brief Copy @a value to each component of @a variable 's type."""
        if isinstance(variable, KratosMultiphysics.BoolVariable):
            return bool(value)
        elif isinstance(variable, KratosMultiphysics.IntegerVariable):
            return int(value)
        elif isinstance(variable, KratosMultiphysics.DoubleVariable):
            return float(value)
        elif isinstance(variable, KratosMultiphysics.Array1DVariable3):
            c = float(value)
            return KratosMultiphysics.Array3([c, c, c])
        elif isinstance(variable, KratosMultiphysics.MatrixVariable):
            c = float(value)
            return KratosMultiphysics.Matrix([[c, c, c], [c, c, c], [c, c, c]])
        else:
            raise ValueError(f"Unsupported variable type: {type(variable)}")


if __name__ == "__main__":
    import argparse
    import pathlib

    parser = argparse.ArgumentParser("MakeTestMDPAs")
    parser.add_argument("-o",
                        "--output",
                        dest = "output",
                        type = pathlib.Path,
                        required = True,
                        help = "Output file path to write to.")
    parser.add_argument("-n",
                        "--number-of-subdivisions",
                        dest = "number_of_subdivisions",
                        type = int,
                        default = 5,
                        help = "Mesh subdivision depth.")
    args = parser.parse_args()

    generator = MDPAGenerator()
    model = KratosMultiphysics.Model()
    root_model_part = generator.MakeRootModelPart(model, number_of_subdivisions = args.number_of_subdivisions)
    generator.MakeSubModelParts(root_model_part)

    args.output.parent.mkdir(exist_ok = True, parents = True)
    generator.Write(root_model_part, args.output)
