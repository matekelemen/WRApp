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
import pathlib
import os


class Launcher(WRApp.WRAppClass):

    def __init__(self, arguments: argparse.Namespace):
        super().__init__()

        self.__working_directory: pathlib.Path = arguments.working_directory
        current_directory = os.getcwd()
        try:
            os.chdir(str(self.__working_directory))

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

            # Import required applications and add classes to the registry
            # Items are expected under the 'registry_extensions' key in the following format:
            # {
            #   "source" : "", // <== full module path to the class to import
            #   "destination"  // <== path in RuntimeRegistry to register the imported class
            # }
            if self.__parameters.Has("registry_extensions"):
                for item in self.__parameters["registry_extensions"].values():
                    WRApp.ImportAndRegister(item["source"].GetString(),
                                            item["destination"].GetString())

        finally:
            os.chdir(current_directory)


    def Launch(self) -> None:
        current_directory = os.getcwd()
        try:
            os.chdir(str(self.__working_directory))
            model = KratosMultiphysics.Model()
            solver: WRApp.AsyncSolver = WRApp.RegisteredClassFactory(
                self.__parameters["solver"]["type"].GetString(),
                model,
                self.__parameters["solver"]["parameters"]
            )
            with solver.RunSolutionLoop() as solution_loop:
                solution_loop()

        finally:
            os.chdir(current_directory)


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        """ @details @code
            {
                "registry_extensions" : [],
                "solver" : {
                    "type" : "",
                    "parameters" : {}
                }
            }
            @endcode
        """
        return KratosMultiphysics.Parameters(R"""{
            "registry_extensions" : [],
            "solver" : {
                "type" : "",
                "parameters" : {}
            }
        }""")