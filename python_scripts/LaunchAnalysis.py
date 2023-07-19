""" @author Máté Kelemen"""

__all__ = [
    "LaunchAnalysis"
]

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp

# --- STD Imports ---
import pathlib


class Launcher:

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        self.__model = model
        self.__parameters = parameters
        parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())


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
        return KratosMultiphysics.Parameters(R"""{
            "preprocessors" : [],
            "solver" : {
                "type" : "",
                "parameters" : {}
            },
            "postprocessors" : []
        }""")



class LaunchAnalysis(WRApp.WRAppClass, KratosMultiphysics.Operation):
    """ @brief Set up, execute, and tear down an analysis based on an input JSON file.
        @classname Launch
    """

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        WRApp.WRAppClass.__init__(self)
        KratosMultiphysics.Operation.__init__(self)
        parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())

        project_parameters: KratosMultiphysics.Parameters
        input_path = pathlib.Path(parameters["project_parameters"].GetString())
        if input_path.exists():
            if input_path.is_file():
                with open(input_path, "r") as file:
                    project_parameters = KratosMultiphysics.Parameters(file.read())
            else:
                raise FileExistsError(f"Expecting a JSON file, but found a directory: {input_path}")
        else:
            raise FileNotFoundError(f"Input JSON not found: {input_path}")

        self.__launcher = Launcher(model, project_parameters)


    def Execute(self) -> None:
        self.__launcher.Preprocess()
        self.__launcher.Launch()
        self.__launcher.Postprocess()


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters(R"""{
            "project_parameters" : ""
        }""")



WRApp.CLI.AddOperation(LaunchAnalysis)
