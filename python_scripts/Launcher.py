""" @author Máté Kelemen"""

__all__ = [
    "Launcher"
]

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp

# --- STD Imports ---
import argparse


class Launcher(WRApp.WRAppClass):
    """ @brief Set up, execute, and tear down an analysis based on an input JSON file."""

    def __init__(self, arguments: argparse.Namespace):
        super().__init__()

        self.__model = KratosMultiphysics.Model()

        # Parse input JSON
        self.__parameters: KratosMultiphysics.Parameters
        if arguments.input_path.exists():
            if arguments.input_path.is_file():
                with open(arguments.input_path, "r") as file:
                    self.__parameters = KratosMultiphysics.Parameters(file.read())
            else:
                raise FileExistsError(f"Expecting a JSON file, but found a directory: {arguments.input_path}")
        else:
            raise FileNotFoundError(f"Input JSON not found: {arguments.input_path}")

        # Validate required parts of the input parameters
        self.__parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())


    def Preprocess(self) -> None:
        """ @brief Instantiate and execute all processes/operations defined in "preprocessors" of the input parameters."""
        for operation_parameters in self.__parameters["preprocessors"].values():
            WRApp.RegisteredClassFactory(
                operation_parameters["type"].GetString(),
                self.__model,
                operation_parameters["parameters"]
            ).Execute()


    def Launch(self) -> None:
        self.Preprocess()
        solver: WRApp.AsyncSolver = WRApp.RegisteredClassFactory(
            self.__parameters["solver"]["type"].GetString(),
            self.__model,
            self.__parameters["solver"]["parameters"]
        )
        with solver.RunSolutionLoop() as solution_loop:
            solution_loop()
        self.Postprocess()


    def Postprocess(self) -> None:
        """ @brief Instantiate and execute all processes/operations defined in "postprocessors" of the input parameters."""
        for operation_parameters in self.__parameters["postprocessors"].values():
            WRApp.RegisteredClassFactory(
                operation_parameters["type"].GetString(),
                self.__model,
                operation_parameters["parameters"]
            ).Execute()


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        """ @details @code
            {
                "preprocessors" : [],
                "solver" : {
                    "type" : "",
                    "parameters" : {}
                },
                "postprocessors" : []
            }
            @endcode
        """
        return KratosMultiphysics.Parameters(R"""{
            "preprocessors" : [],
            "solver" : {
                "type" : "",
                "parameters" : {}
            },
            "postprocessors" : []
        }""")
