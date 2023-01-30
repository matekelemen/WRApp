"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics


def MakeRootModelPart(model: KratosMultiphysics.Model,
                      name: str = "root",
                      buffer_size: int = 3) -> KratosMultiphysics.ModelPart:
    """@brief Create a @ref ModelPart on a unit square."""
    model_part = model.CreateModelPart(name)
    model_part.ProcessInfo[KratosMultiphysics.DOMAIN_SIZE] = 3
    model_part.SetBufferSize(buffer_size)

    nodal_variables = (
        #KratosMultiphysics.COMPUTE_DYNAMIC_TANGENT,     # bool
        KratosMultiphysics.REFINEMENT_LEVEL,            # int
        KratosMultiphysics.DELTA_TIME,                  # double
        KratosMultiphysics.ROTATION,                    # double array
        #KratosMultiphysics.DEFORMATION_GRADIENT         # double matrix
    )

    element_variables = (
        KratosMultiphysics.IS_RESTARTED,                # bool
        KratosMultiphysics.LOAD_RESTART,                # int
        KratosMultiphysics.START_TIME,                  # double
        KratosMultiphysics.DELTA_ROTATION,              # double array
        KratosMultiphysics.PK2_STRESS_TENSOR            # double matrix
    )

    condition_variables = (
        KratosMultiphysics.COMPUTE_LUMPED_MASS_MATRIX,  # bool
        KratosMultiphysics.FIRST_TIME_STEP,             # int
        KratosMultiphysics.END_TIME,                    # double
        KratosMultiphysics.REACTION_MOMENT,             # double array
        KratosMultiphysics.CAUCHY_STRESS_TENSOR         # double matrix
    )

    # Add historical variables
    for variable in nodal_variables:
        model_part.AddNodalSolutionStepVariable(variable)

    # Create mesh
    root_element = KratosMultiphysics.Quadrilateral2D4(
        KratosMultiphysics.Node(1, 0.0, 0.0, 0.0),
        KratosMultiphysics.Node(2, 0.0, 1.0, 0.0),
        KratosMultiphysics.Node(3, 1.0, 1.0, 0.0),
        KratosMultiphysics.Node(4, 1.0, 0.0, 0.0)
    )
    mesh_parameters = KratosMultiphysics.Parameters("""{
        "number_of_divisions" : 5,
        "element_name" : "Element2D3N",
        "create_skin_sub_model_part" : true,
        "condition_name" : "LineCondition"
    }""")
    KratosMultiphysics.StructuredMeshGeneratorProcess(root_element,
                                                      model_part,
                                                      mesh_parameters).Execute()

    # Add element variables to **all** elements
    for element in model_part.Elements:
        for variable in element_variables:
            element[variable] # <== this adds a null variable to the element

    # Add condition variables to **all** conditions
    for condition in model_part.Conditions:
        for variable in condition_variables:
            condition[variable] # <== this adds a null variable to the element

    return model_part


def MakeSubModelParts(root_model_part: KratosMultiphysics.ModelPart) -> "list[KratosMultiphysics.ModelPart]":
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
    parser.add_argument("--overwrite",
                        dest = "overwrite",
                        action = "store_const",
                        const = True,
                        default = False,
                        help = "Overwrite the output file if it already exists.")
    args = parser.parse_args()

    model = KratosMultiphysics.Model()
    root_model_part = MakeRootModelPart(model)
    MakeSubModelParts(root_model_part)

    if args.output.exists() and not args.overwrite:
        raise FileExistsError(f"File already exists: {args.output}")

    args.output.parent.mkdir(exist_ok = True, parents = True)
    KratosMultiphysics.ModelPartIO(str(args.output), KratosMultiphysics.IO.WRITE).WriteModelPart(root_model_part)
