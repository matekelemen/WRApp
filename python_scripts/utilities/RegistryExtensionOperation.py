"""@author Máté Kelemen"""

__all__ = [
    "RegistryExtensionOperation"
]

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp


class RegistryExtensionOperation(KratosMultiphysics.Operation, WRApp.WRAppClass):
    """ @brief Extend the WRApp registry with imported objects.
        @details Input parameters are expected as a list of string pairs specifying
                 the object to import and its destination in the registry. For example:
                 @code
                 {
                    "extensions" : [
                        {
                            "source" : "KratosMultiphysics.FluidDynamicsApplication.fluid_dynamics_analysis.FluidDynamicsAnalysis",
                            "destination" : "WRApplication.FluidDynamicsAnalysis"
                        }
                    ]
                 }
                 @endcode
                 After executing this operation with the parameters above, the @a FluidDynamicsAnalysis class
                 will be available in the @ref RuntimeRegistry under the @a WRApplication.FluidDynamicsAnalysis path.
    """

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        KratosMultiphysics.Operation.__init__(self)
        WRApp.WRAppClass.__init__(self)
        self.__parameters = parameters
        self.__parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())


    def Execute(self) -> None:
        for item in self.__parameters["extensions"].values():
            WRApp.ImportAndRegister(item["source"].GetString(), item["destination"].GetString())


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        """ @code
            {
                "extensions" : []
            }
            @endcode"""
        return KratosMultiphysics.Parameters("""{
            "extensions" : []
        }""")
