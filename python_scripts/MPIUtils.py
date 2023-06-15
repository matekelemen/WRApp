"""@author Máté Kelemen"""

__all__ = ["MPIUtils"]

# --- Core Imports ---
import KratosMultiphysics

# --- WRApplication Imports ---
from KratosMultiphysics import WRApplication as WRApp


## @addtogroup WRApplication
## @{
## @addtogroup utilities
## @{


class MPIUtils:
    """ @brief Utility class collecting functions requiring MPI synchronization.
        @classname MPIUtils
    """

    @staticmethod
    def MPIUnion(container: "set[str]", data_communicator: KratosMultiphysics.DataCommunicator) -> "set[str]":
        """ @brief Return a union of strings across all MPI ranks."""
        return set(WRApp.MPIAllGatherVStrings(list(container), data_communicator))


    @staticmethod
    def ExtractNodalSolutionStepDataNames(model_part: KratosMultiphysics.ModelPart) -> "list[str]":
        """ @brief Reduce all nodal historical variable names in the input @ref ModelPart across all MPI ranks."""
        data_communicator = model_part.GetCommunicator().GetDataCommunicator()
        local_names = model_part.GetHistoricalVariablesNames()
        output =  list(MPIUtils.MPIUnion(set(local_names), data_communicator))
        return output


    @staticmethod
    def ExtractNodalDataNames(model_part: KratosMultiphysics.ModelPart, check_mesh_consistency: bool = False) -> "list[str]":
        """ @brief Reduce all nodal non-historical variable names in the input @ref ModelPart across all MPI ranks.
            @details Nodes in the input @ref ModelPart on a given rank are assumed to share the list of variables.
        """
        data_communicator = model_part.GetCommunicator().GetDataCommunicator()
        local_names = model_part.GetNonHistoricalVariablesNames(model_part.Nodes, check_mesh_consistency)
        output =  list(MPIUtils.MPIUnion(set(local_names), data_communicator))
        return output


    @staticmethod
    def ExtractNodalFlagNames(model_part: KratosMultiphysics.ModelPart) -> "list[str]":
        """ @brief Get the names of all currently defined global @ref Flags."""
        return WRApp.Utils.GetGlobalFlagNames()


    @staticmethod
    def ExtractElementDataNames(model_part: KratosMultiphysics.ModelPart, check_mesh_consistency: bool = False) -> "list[str]":
        """ @brief Reduce all element variable names in the input @ref ModelPart across all MPI ranks.
            @details Elements in the input @ref ModelPart on a given rank are assumed to share the list of variables.
        """
        data_communicator = model_part.GetCommunicator().GetDataCommunicator()
        local_names = model_part.GetNonHistoricalVariablesNames(model_part.Elements, check_mesh_consistency)
        output =  list(MPIUtils.MPIUnion(set(local_names), data_communicator))
        return output


    @staticmethod
    def ExtractElementFlagNames(model_part: KratosMultiphysics.ModelPart) -> "list[str]":
        return WRApp.Utils.GetGlobalFlagNames()


    @staticmethod
    def ExtractConditionDataNames(model_part: KratosMultiphysics.ModelPart, check_mesh_consistency: bool = False) -> "list[str]":
        data_communicator = model_part.GetCommunicator().GetDataCommunicator()
        local_names = model_part.GetNonHistoricalVariablesNames(model_part.Conditions, check_mesh_consistency)
        output =  list(MPIUtils.MPIUnion(set(local_names), data_communicator))
        return output


    @staticmethod
    def ExtractConditionFlagNames(model_part: KratosMultiphysics.ModelPart) -> "list[str]":
        return WRApp.Utils.GetGlobalFlagNames()


## @}
## @}
