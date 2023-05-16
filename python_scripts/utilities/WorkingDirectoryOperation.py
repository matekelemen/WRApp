"""@author Máté Kelemen"""

__all__ = [
    "WorkingDirectoryOperation"
]

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp

# --- STD Imports ---
import os


class WorkingDirectoryOperation(KratosMultiphysics.Operation, WRApp.WRAppClass):
    """ @brief Change the working directory.
        @details Input parameters:
                 @code
                 {
                    "path" : "path_to_new_working_directory"
                 }
                 @endcode
    """

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        KratosMultiphysics.Operation.__init__(self)
        WRApp.WRAppClass.__init__(self)
        self.__parameters = parameters
        self.__parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())


    def Execute(self) -> None:
        os.chdir(self.__parameters["path"].GetString())


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        """ @code
            {
                "path" : ""
            }
            @endcode
        """
        return KratosMultiphysics.Parameters("""{
            "path" : ""
        }""")
