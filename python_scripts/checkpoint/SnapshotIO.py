"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp

# --- STD Imports ---
import abc
import pathlib


## @addtogroup WRApplication
## @{
## @addtogroup checkpointing
## @{


class SnapshotIO(WRApp.WRAppClass):
    """ @brief Interface for performing @ref Snapshot input/output operations.
        @classname SnapshotIO
        @details Default parameters:
                 @code
                 {
                    "nodal_historical_variables" : [],
                    "nodal_variables" : [],
                    "nodal_flags" : [],
                    "element_variables" : [],
                    "element_flags" : [],
                    "condition_variables" : [],
                    "condition_flags" : []
                 }
                 @endcode
    """

    def __init__(self,
                 parameters: KratosMultiphysics.Parameters):
        super().__init__()
        self._parameters = parameters
        self._parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())


    def __call__(self, model_part: KratosMultiphysics.ModelPart) -> None:
        self._GetOperation(model_part).Execute()


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters(R"""{
            "nodal_historical_variables" : [],
            "nodal_variables" : [],
            "nodal_flags" : [],
            "element_variables" : [],
            "element_flags" : [],
            "condition_variables" : [],
            "condition_flags" : []
        }""")


    @abc.abstractmethod
    def _GetOperation(self, model_part: KratosMultiphysics.ModelPart) -> KratosMultiphysics.Operation:
        """ @brief Get the IO operation to execute on the provided @ref ModelPart."""
        return KratosMultiphysics.Operation()



class SnapshotFSIO(SnapshotIO):
    """ @brief Base class for @ref Snapshot s that store their data on the filesystem.
        @classname SnapshotFSIO
    """

    def __init__(self, parameters: KratosMultiphysics.Parameters):
        super().__init__(parameters)


    @abc.abstractmethod
    def GetID(self) -> WRApp.CheckpointID:
        """ @brief Read data from a file that identifies a @ref Snapshot."""
        return WRApp.CheckpointID()


    @abc.abstractmethod
    def GetPath(self, id: WRApp.CheckpointID = None) -> pathlib.Path:
        """ @brief Return the path to the associated file given the checkpoint ID, or the pattern if the ID is not provided."""
        pass


## @}
## @}
