""" @author Máté Kelemen"""

__all__ = [
    "GenerateXDMFProcess"
]

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp
from .GenerateHDF5Journal import GenerateHDF5Journal
from .GenerateXDMF import GenerateXDMF

# --- STD Imports ---
import typing


class GenerateXDMFProcess(KratosMultiphysics.Process, WRApp.WRAppClass):
    """ @brief Generate XDMF output for an existing set of HDF5 output files.
        @classname GenerateXDMFProcess
        @details Default parameters:
                 @code
                 {
                    "file_pattern": "",                         // <== input file pattern compatible with ModelPartPattern
                    "mesh_prefix" : "/ModelData",               // <== prefix of the mesh within HDF5 files
                    "results_prefix" : "/ResultsData",          // <== prefix of the results within HDF5 files
                    "journal_path" : "xdmf_output.journal",     // <== journal output path that gets written as an intermediate step
                    "batch_size" : -1,                          // <== number of input files to process per output xdmf
                    "output_pattern" : "batch_<batch>.xdmf",    // <== output file name pattern; may contain the "<batch>" placeholder
                    "verbose" : false                           // <== print status messages
                 }
                 @endcode
    """

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        KratosMultiphysics.Process.__init__(self)
        WRApp.WRAppClass.__init__(self)

        parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())
        self.__operations: "list[KratosMultiphysics.Operation]" = []

        operation_types = self.__GetOperationTypes()
        for operation_type in operation_types:
            operation_parameters = KratosMultiphysics.Parameters()
            default_parameters: KratosMultiphysics.Parameters = operation_type.GetDefaultParameters()
            for key in default_parameters.keys():
                if parameters.Has(key):
                    operation_parameters.AddValue(key, parameters[key])
            self.__operations.append(operation_type(model, operation_parameters))



    def ExecuteFinalize(self) -> None:
        for operation in self.__operations:
            operation.Execute()


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        default_parameters = KratosMultiphysics.Parameters()
        for operation_type in cls.__GetOperationTypes():
            for key, value in operation_type.GetDefaultParameters().items():
                if not default_parameters.Has(key):
                    default_parameters.AddValue(key, value)
        return default_parameters


    @classmethod
    def __GetOperationTypes(cls) -> "list[typing.Type[KratosMultiphysics.Operation]]":
        return [GenerateHDF5Journal, GenerateXDMF]



def Factory(parameters: KratosMultiphysics.Parameters,
            model: KratosMultiphysics.Model) -> GenerateXDMFProcess:
    return GenerateXDMFProcess(model, parameters["Parameters"])
