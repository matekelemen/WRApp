"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics


def MakeModel(name: str = "test",
              buffer_size: int = 3) -> "tuple[KratosMultiphysics.Model, KratosMultiphysics.ModelPart]":
    model = KratosMultiphysics.Model()

    model_part = model.CreateModelPart(name)
    model_part.SetBufferSize(buffer_size)

    nodal_variables = (
        KratosMultiphysics.COMPUTE_DYNAMIC_TANGENT,     # bool
        KratosMultiphysics.DOMAIN_SIZE,                 # int
        KratosMultiphysics.DELTA_TIME,                  # double
        KratosMultiphysics.ROTATION,                    # double array
        KratosMultiphysics.DEFORMATION_GRADIENT         # double matrix
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
        "number_of_divisions" : 100,
        "element_name" : "Element2D3N"
    }""")
    KratosMultiphysics.StructuredMeshGeneratorProcess(root_element,
                                                      model_part,
                                                      mesh_parameters).Execute()

    # Add element variables to **all** elements
    KratosMultiphysics.BoolVariable
    for element in model_part.Elements:
        for variable in element_variables:
            element[variable] # <== this adds a null variable to the element

    # Add conditions on all root element boundaries


    return model, model_part


if __name__ == "__main__":
    model, model_part = MakeModel()
