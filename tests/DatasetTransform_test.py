""" @author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp


class TestDatasetTransfer(WRApp.TestCase):

    def test_NoTransform(self) -> None:
        model = KratosMultiphysics.Model()
        source_model_part = model.CreateModelPart("source")
        target_model_part = model.CreateModelPart("target")

        source_model_part.AddNodalSolutionStepVariable(KratosMultiphysics.REACTION)

        source_nodes = [source_model_part.CreateNewNode(1, 0.0, 0.0, 0.0),
                        source_model_part.CreateNewNode(2, 1.0, 0.0, 0.0),
                        source_model_part.CreateNewNode(3, 1.0, 1.0, 0.0),
                        source_model_part.CreateNewNode(4, 0.0, 1.0, 0.0)]
        source_model_part.CreateNewElement("Element2D4N", 1, [1, 2, 3, 4], KratosMultiphysics.Properties(0))
        source_nodes[0].SetSolutionStepValue(KratosMultiphysics.REACTION, [1.0, 2.0, 3.0])
        source_nodes[1].SetSolutionStepValue(KratosMultiphysics.REACTION, [4.0, 5.0, 6.0])
        source_nodes[2].SetSolutionStepValue(KratosMultiphysics.REACTION, [7.0, 8.0, 9.0])
        source_nodes[3].SetSolutionStepValue(KratosMultiphysics.REACTION, [10.0, 11.0, 12.0])
        source_interface_model_part = source_model_part.CreateSubModelPart("source_interface")
        source_interface_model_part.AddNodes([2, 3])
        source_interface_model_part.CreateNewCondition("LineCondition2D2N", 1, [2, 3], KratosMultiphysics.Properties(0))

        target_nodes = [target_model_part.CreateNewNode(5, 1.0, 0.2, 0.0),
                        target_model_part.CreateNewNode(6, 2.0, 0.2, 0.0),
                        target_model_part.CreateNewNode(7, 2.0, 0.8, 0.0),
                        target_model_part.CreateNewNode(8, 1.0, 0.8, 0.0)]
        target_model_part.CreateNewElement("Element2D4N", 2, [5, 6, 7, 8], KratosMultiphysics.Properties(0))
        for node in target_nodes:
            node[KratosMultiphysics.DISPLACEMENT] = [0.0, 0.0, 0.0]
        target_interface_model_part = target_model_part.CreateSubModelPart("target_interface")
        target_interface_model_part.AddNodes([6, 7])
        target_interface_model_part.CreateNewCondition("LineCondition2D2N", 2, [6, 7], KratosMultiphysics.Properties(0))


        transfer_parameters = KratosMultiphysics.Parameters("""{
            "source" : {
                "model_part_name" : "source.source_interface",
                "variables" : [
                    {
                        "entity_type" : "nodal_historical",
                        "variable_name" : "REACTION"
                    }
                ]
            },
            "mapper" : {
                "mapper_type" : "nearest_element"
            },
            "target" : {
                "model_part_name" : "target.target_interface",
                "variables" : [
                    {
                        "entity_type" : "nodal",
                        "variable_name" : "DISPLACEMENT"
                    }
                ]
            }
        }""")
        operation = WRApp.MappedDatasetTransform(model, transfer_parameters)

        self.assertVectorAlmostEqual(target_nodes[1][KratosMultiphysics.DISPLACEMENT], [0.0, 0.0, 0.0])
        self.assertVectorAlmostEqual(target_nodes[2][KratosMultiphysics.DISPLACEMENT], [0.0, 0.0, 0.0])

        operation.Execute()

        self.assertVectorAlmostEqual(target_nodes[1][KratosMultiphysics.DISPLACEMENT], [23/5.0, 28/5.0, 33/5.0])
        self.assertVectorAlmostEqual(target_nodes[2][KratosMultiphysics.DISPLACEMENT], [32/5.0, 37/5.0, 42/5.0])


if __name__ == "__main__":
    WRApp.TestMain()
