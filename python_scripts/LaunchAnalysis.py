""" @author Máté Kelemen"""

__all__ = [
    "LaunchAnalysis"
]

# --- Core Imports ---
import KratosMultiphysics
from KratosMultiphysics.analysis_stage import AnalysisStage

# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp

# --- STD Imports ---
import pathlib
import importlib


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
        solver_type_name: str = self.__parameters["solver"]["type"].GetString()
        if WRApp.IsRegisteredPath(solver_type_name):
            solver: WRApp.AsyncSolver = WRApp.RegisteredClassFactory(
                solver_type_name,
                self.__model,
                self.__parameters["solver"]["parameters"])
            with solver.RunSolutionLoop() as solution_loop:
                solution_loop()
        else:
            analysis: AnalysisStage
            if KratosMultiphysics.Registry.HasItem(f"{solver_type_name}.Prototype"):
                analysis: AnalysisStage = KratosMultiphysics.Registry[f"{solver_type_name}.Prototype"].Create(
                    self.__model,
                    self.__parameters["solver"]["parameters"])
            elif KratosMultiphysics.Registry.HasItem(f"{solver_type_name}.ModuleName"):
                class_name: str = solver_type_name.split(".")[-1]
                module_name: str = KratosMultiphysics.Registry[f"{solver_type_name}.ModuleName"]
                module = importlib.import_module(module_name)
                if hasattr(module, class_name):
                    prototype = getattr(module, class_name)
                    analysis = prototype(
                        self.__model,
                        self.__parameters["solver"]["parameters"])
                else:
                    raise NameError(f"cannot find analysis '{class_name}' in module '{module_name}'")
            else:
                class_path: list[str] = solver_type_name.split(".")
                module = importlib.import_module(".".join(class_path[:-1]))
                if hasattr(module, class_path[-1]):
                    prototype = getattr(module, class_path[-1])
                    analysis = prototype(
                        self.__model,
                        self.__parameters["solver"]["parameters"])
                else:
                    raise NameError(f"cannot find analysis '{class_path[-1]}' in module '{'.'.join(class_path[:-1])}'")
            analysis.Run()


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

        if project_parameters.Has("analysis_stage"):
            analysis_stage_name: str = project_parameters["analysis_stage"].GetString()
        else:
            raise ValueError(f"Input configuration '{input_path}' does not define 'analysis_stage'.")
        launcher_parameters: KratosMultiphysics.Parameters = KratosMultiphysics.Parameters(
            R"""{
                "solver" : {
                    "type" : ""
                }
            }""")
        launcher_parameters["solver"]["type"].SetString(analysis_stage_name)
        launcher_parameters["solver"].AddValue("parameters", project_parameters)
        self.__launcher: Launcher = Launcher(model, launcher_parameters)


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
