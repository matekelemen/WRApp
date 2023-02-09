"""@author Máté Kelemen"""

__all__ = ["HDF5SnapshotInput", "HDF5SnapshotOutput"]

# --- Core Imports ---
import KratosMultiphysics

# --- HDF5 Imports ---
from KratosMultiphysics.HDF5Application.core import operations as HDF5Operations
from KratosMultiphysics.HDF5Application.core.file_io import OpenHDF5File

# --- WRApp Imports ---
from KratosMultiphysics import WRApplication as WRApp
from .SnapshotIO import SnapshotIO
from ..mpi_utilities import MPIUnion

# --- STD Imports ---
import abc
import pathlib


class HDF5SnapshotIO(SnapshotIO):
    """@brief Base class with common functionality to writing/loading snapshots to/from disk."""

    def __init__(self, parameters: KratosMultiphysics.Parameters):
        self.__parameters = parameters
        self.__parameters.RecursivelyValidateAndAssignDefaults(self.GetDefaultParameters())


    def GetID(self) -> WRApp.CheckpointID:
        model = KratosMultiphysics.Model()
        model_part = model.CreateModelPart("temporary")
        with OpenHDF5File(self.__GetInputParameters(), model_part) as file:
            HDF5Operations.ReadProcessInfo(self.__parameters["operation_settings"])(model_part, file)
        step = model_part.ProcessInfo[KratosMultiphysics.STEP]
        analysis_path = model_part.ProcessInfo[WRApp.ANALYSIS_PATH]
        model.DeleteModelPart("temporary")
        return WRApp.CheckpointID(step, analysis_path)


    def GetPath(self, id: WRApp.CheckpointID = None) -> pathlib.Path():
        string = self.__parameters["io_settings"]["file_name"].GetString()
        if id is None:
            string = WRApp.CheckpointPattern(string).Apply({
                "<step>" : str(id.GetStep()),
                "<path_id>" : str(id.GetAnalysisPath())
            })
        return pathlib.Path(string)


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        parameters = KratosMultiphysics.Parameters(R"""{
            "prefix" : "/snapshot_step_<step>_path_<path_id>"
        }""")
        parameters.AddValue("io_settings", cls.GetDefaultIOParameters())
        return parameters


    @property
    def parameters(self) -> KratosMultiphysics.Parameters:
        return self.__parameters


    @staticmethod
    def _ExtractNodalSolutionStepDataNames(model_part: KratosMultiphysics.ModelPart) -> "list[str]":
        data_communicator = model_part.GetCommunicator().GetDataCommunicator()
        local_names = model_part.GetHistoricalVariablesNames()
        output =  list(MPIUnion(set(local_names), data_communicator))
        return output


    @staticmethod
    def _ExtractNodalDataNames(model_part: KratosMultiphysics.ModelPart, check_mesh_consistency: bool = False) -> "list[str]":
        data_communicator = model_part.GetCommunicator().GetDataCommunicator()
        local_names = model_part.GetNonHistoricalVariablesNames(model_part.Nodes, check_mesh_consistency)
        output =  list(MPIUnion(set(local_names), data_communicator))
        return output


    @staticmethod
    def _ExtractNodalFlagNames(model_part: KratosMultiphysics.ModelPart) -> "list[str]":
        return WRApp.GetGlobalFlagNames()


    @staticmethod
    def _ExtractElementDataNames(model_part: KratosMultiphysics.ModelPart, check_mesh_consistency: bool = False) -> "list[str]":
        data_communicator = model_part.GetCommunicator().GetDataCommunicator()
        local_names = model_part.GetNonHistoricalVariablesNames(model_part.Elements, check_mesh_consistency)
        output =  list(MPIUnion(set(local_names), data_communicator))
        return output

    @staticmethod
    def _ExtractElementFlagNames(model_part: KratosMultiphysics.ModelPart) -> "list[str]":
        return WRApp.GetGlobalFlagNames()


    @staticmethod
    def _ExtractConditionDataNames(model_part: KratosMultiphysics.ModelPart, check_mesh_consistency: bool = False) -> "list[str]":
        data_communicator = model_part.GetCommunicator().GetDataCommunicator()
        local_names = model_part.GetNonHistoricalVariablesNames(model_part.Conditions, check_mesh_consistency)
        output =  list(MPIUnion(set(local_names), data_communicator))
        return output


    @staticmethod
    def _ExtractConditionFlagNames(model_part: KratosMultiphysics.ModelPart) -> "list[str]":
        return WRApp.GetGlobalFlagNames()


    @staticmethod
    def _ApplyPrefix(prefix: str,
                     operation_parameters: KratosMultiphysics.Parameters,
                     model_part: KratosMultiphysics.ModelPart) -> None:
        for parameters in operation_parameters["list_of_operations"]:
            prefix_full = WRApp.CheckpointPattern(prefix + "/" + parameters["prefix"].GetString()).Apply(model_part)
            while "//" in prefix_full:
                prefix_full = prefix_full.replace("//", "/")
            parameters["prefix"].SetString(prefix_full)


    @staticmethod
    @abc.abstractmethod
    def GetDefaultIOParameters() -> KratosMultiphysics.Parameters:
        raise RuntimeError("Attempt to call a pure virtual function")


    def __GetInputParameters(self) -> KratosMultiphysics.Parameters:
        """@brief Get IO parameters for reading a file regardless of whether the class is meant for reading or writing."""
        io_parameters = self.GetDefaultIOParameters()
        io_parameters["file_access_mode"].SetString("read_only")
        return io_parameters



class HDF5SnapshotOutput(HDF5SnapshotIO):
    """@brief Output class for writing most data in the model part to an HDF5 snapshot.
       @details Data written: - nodal solution step data
                              - nodal data value
                              - nodal flag
                              - element data value
                              - element flag
                              - condition data value
                              - condition flag
                              - process info
    """

    @staticmethod
    def GetDefaultIOParameters() -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters("""{
            "file_name" : "",
            "file_access_mode" : "read_write",
            "echo_level" : 0
        }""")


    def _GetOperation(self, model_part: KratosMultiphysics.ModelPart) -> HDF5Operations.AggregateOperation:
        # Collect parameters to construct HDF5 operations with
        aggregate_parameters = KratosMultiphysics.Parameters()
        aggregate_parameters.AddString("model_part_name", model_part.Name)

        aggregate_parameters.AddEmptyArray("list_of_operations")
        list_of_operations = aggregate_parameters["list_of_operations"]

        # Operations on variables
        for operation_type, variable_names in (("nodal_solution_step_data_output", self._ExtractNodalSolutionStepDataNames(model_part)),
                                               ("nodal_data_value_output",         self._ExtractNodalDataNames(model_part)),
                                               ("nodal_flag_value_output",         self._ExtractNodalFlagNames(model_part)),
                                               ("element_data_value_output",       self._ExtractElementDataNames(model_part)),
                                               ("element_flag_value_output",       self._ExtractElementFlagNames(model_part)),
                                               ("condition_data_value_output",     self._ExtractConditionDataNames(model_part)),
                                               ("condition_flag_value_output",     self._ExtractConditionFlagNames(model_part))):
            local_parameters = KratosMultiphysics.Parameters()
            local_parameters.AddString("operation_type", operation_type)
            local_parameters.AddStringArray("list_of_variables", variable_names)
            list_of_operations.Append(local_parameters)

        # Other operations
        process_info_parameters = KratosMultiphysics.Parameters("""{
            "operation_type" : "process_info_output"
        }""")
        list_of_operations.Append(process_info_parameters)

        # IO settings
        aggregate_parameters.AddValue("io_settings", self.parameters["io_settings"])

        # Construct the operation and apply the snapshot root prefix
        aggregate_operation = HDF5Operations.AggregateOperation(model_part.GetModel(), aggregate_parameters)
        self._ApplyPrefix(self.parameters["prefix"].GetString(), aggregate_parameters, model_part)

        return aggregate_operation



class HDF5SnapshotInput(HDF5SnapshotIO):
    """@brief Input class for reading most data from an HDF5 snapshot to a model part.
       @details Data read: - nodal solution step data
                           - nodal data value
                           - nodal flag
                           - element data value
                           - element flag
                           - condition data value
                           - condition flag
                           - process info
    """

    @staticmethod
    def GetDefaultIOParameters() -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters("""{
            "file_name" : "",
            "file_access_mode" : "read_only",
            "echo_level" : 0
        }""")


    def _GetOperation(self, model_part: KratosMultiphysics.ModelPart) -> HDF5Operations.AggregateOperation:
        # Collect parameters to construct HDF5 operations with
        aggregate_parameters = KratosMultiphysics.Parameters()
        aggregate_parameters.AddString("model_part_name", model_part.Name)

        aggregate_parameters.AddEmptyArray("list_of_operations")
        list_of_operations = aggregate_parameters["list_of_operations"]

        # Operations on variables
        for operation_type, variable_names in (("nodal_solution_step_data_input", self._ExtractNodalSolutionStepDataNames(model_part)),
                                               ("nodal_data_value_input",         self._ExtractNodalDataNames(model_part)),
                                               ("nodal_flag_value_input",         self._ExtractNodalFlagNames(model_part)),
                                               ("element_data_value_input",       self._ExtractElementDataNames(model_part)),
                                               ("element_flag_value_input",       self._ExtractElementFlagNames(model_part)),
                                               ("condition_data_value_input",     self._ExtractConditionDataNames(model_part)),
                                               ("condition_flag_value_input",     self._ExtractConditionFlagNames(model_part))):
            local_parameters = KratosMultiphysics.Parameters()
            local_parameters.AddString("operation_type", operation_type)
            local_parameters.AddStringArray("list_of_variables", variable_names)
            list_of_operations.Append(local_parameters)

        # Other operations
        process_info_parameters = KratosMultiphysics.Parameters("""{
            "operation_type" : "process_info_input"
        }""")
        list_of_operations.Append(process_info_parameters)

        # IO settings
        aggregate_parameters.AddValue("io_settings", self.parameters["io_settings"])

        # Construct the operation and apply the snapshot root prefix
        aggregate_operation = HDF5Operations.AggregateOperation(model_part.GetModel(), aggregate_parameters)
        self._ApplyPrefix(self.parameters["prefix"].GetString(), aggregate_parameters, model_part)

        return aggregate_operation
