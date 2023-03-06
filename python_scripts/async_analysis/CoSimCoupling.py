""" @author Máté Kelemen"""

__all__ = [
    "CoSimCoupling"
]

# --- Core Imports ---
import KratosMultiphysics

# --- CoSim Imports ---
from KratosMultiphysics.CoSimulationApplication.factories.helpers import CreateDataTransferOperators
from KratosMultiphysics.CoSimulationApplication.base_classes.co_simulation_data_transfer_operator import CoSimulationDataTransferOperator
from KratosMultiphysics.CoSimulationApplication.coupling_interface_data import CouplingInterfaceData

# --- WRApp Imports ---
from ..ToDoException import ToDoException
import KratosMultiphysics.WRApplication as WRApp


class CouplingSequenceItem(KratosMultiphysics.Operation):
    """ @private"""

    def __init__(self,
                 source_dataset: CouplingInterfaceData,
                 transformation: CoSimulationDataTransferOperator,
                 transformation_parameters: KratosMultiphysics.Parameters,
                 target_dataset: CouplingInterfaceData):
        super().__init__()
        self.__source_dataset = source_dataset
        self.__transformation = transformation
        self.__transformation_parameters = transformation_parameters
        self.__target_dataset = target_dataset


    def Execute(self) -> None:
        self.__transformation.TransferData(self.__source_dataset,
                                           self.__target_dataset,
                                           self.__transformation_parameters)


## @addtogroup WRApplication
## @{
## @addtogroup AsyncAnalysis
## @{


class CoSimCoupling(KratosMultiphysics.Operation, WRApp.WRAppClass):
    """ @brief Wrapper for CoSimulationApplication coupling procedures.
        @classname CoSimCoupling
        @details Default parameters:
                 @code
                 {
                    "interface_datasets" : []
                    "transform_operators" : {},
                    "coupling_sequence" : [],
                    "verbosity" : 2
                 }
                 @endcode
                 @a "transform_operators" is forwarded to @ref CoSimulationApplication.factories.helpers.CreateDataTransferOperators.
                 @a "coupling_sequence" is forwarded to CoSimulationApplication.factories.helpers.CreateCouplingOperations.
        @details Items in @a "interface_datasets" represent exposed sets of data on partition interfaces. The expected format
                 of each item:
                 @code
                 {
                    "name" : "",            // <== name of the dataset
                    "partition_name" : "",  // <== name of related partition
                    "model_part_name" : "", // <== name of the ModelPart within the partition the dataset is defined on
                    "dimension" : 0,        // <== number of components in each item of the dataset
                    "variable_name" : ""    // <== name of the variable the dataset refers to
                 }
                 @endcode
        @details Each item in @a "coupling_sequence" defines a fetch-transform-write operation:
                 - fetch a specific dataset from a source partition
                 - transform the fetched dataset
                 - write the transformed dataset to a dataset defined in the target partition
                 Items are expected in the following format:
                 @code
                 {
                    "source_dataset" : "",  // <== name of the dataset to fetch
                    "transform" : {
                        "operator" : "",    // <== name of the dataset transform/transfer operator (defined in "transform_operators")
                        "parameters" : {}   // <== parameters to pass on the operator
                    },
                    "target_dataset" : ""   // <== name of the dataset to write to
                 }
                 @endcode
    """

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 data_communicator: KratosMultiphysics.DataCommunicator,
                 parameters: KratosMultiphysics.Parameters):
        KratosMultiphysics.Operation.__init__(self)
        WRApp.WRAppClass.__init__(self)
        self.__parameters = parameters
        self.__data_communicator = data_communicator
        parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())

        # Define exposed datasets on partition interfaces
        self.__datasets = self.__MakeDatasets(model, self.parameters["interface_datasets"])

        ## @todo Define coupling operators
        if not len(self.__parameters["coupling_operations"].items()):
            raise ToDoException('"coupling_operations" are not supported yet')

        # Map transform operator names to the operators they represent
        self.__transform_operators = self.__MakeTransformOperators(self.parameters["transform_operators"],
                                                                   self.__data_communicator,
                                                                   self.parameters["verbosity"].GetInt())

        # Create a list of operations that must be executed in order at each synchronization
        self.__coupling_sequence = self.__MakeCouplingSequence(self.__datasets,
                                                               self.__transform_operators,
                                                               self.parameters["coupling_sequence"])


    def Execute(self) -> None:
        """ @brief Execute all items in the coupling sequence in the order they were defined."""
        for operation in self.__coupling_sequence:
            operation.Execute()


    ## @name Properties
    ## @{


    @property
    def parameters(self) -> KratosMultiphysics.Parameters:
        return self.__parameters


    ## @}
    ## @name Static Members
    ## @{


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        """ @code
            {
                "coupling_operations" : {},
                "transform_operators" : {},
                "coupling_sequence" : [],
                "verbosity" : 2
            }
            @endcode
        """
        return KratosMultiphysics.Parameters(R"""{
            "coupling_operations" : {},
            "transform_operators" : {},
            "coupling_sequence" : [],
            "verbosity" : 2
        }""")


    @classmethod
    def __MakeDatasets(cls,
                       model: KratosMultiphysics.Model,
                       parameters: KratosMultiphysics.Parameters) -> "dict[str,CouplingInterfaceData]":
        """ @brief Define exposed interface datasets that can later be fetched from / written to.
            @returns A map associating dataset names to their respective @ref CouplingInterfaceData instances.
        """
        output: "dict[str,CouplingInterfaceData]" = {}
        for dataset_parameters in parameters.values():
            # dataset_parameters expected in the following format:
            # {
            #     "name" : "",
            #     "partition_name" : "",
            #     "model_part_name" : "",
            #     "dimension" : 0,
            #     "variable_name" : ""
            # }
            dataset_name = dataset_parameters["name"].GetString()
            partition_name = dataset_parameters["partition_name"].GetString()

            ## @todo Make sure that the specified ModelPart is a sub model part of the partititon
            #model_part_name = dataset_parameters["model_part_name"].GetString()

            # Translate input parameters into those required by CouplingInterfaceData
            forwarded_parameters = KratosMultiphysics.Parameters()
            forwarded_parameters.AddValue("model_part_name", dataset_parameters["model_part_name"])
            forwarded_parameters.AddValue("dimension", dataset_parameters["dimension"])
            forwarded_parameters.AddValue("variable_name", dataset_parameters["variable_name"])

            if dataset_name in output:
                raise NameError(f"Duplicate dataset names in {parameters}")

            output[dataset_name] = CouplingInterfaceData(forwarded_parameters,
                                                         model,
                                                         dataset_name,
                                                         partition_name)

            # Feed extra entries added by CouplingInterfaceData's constructor
            dataset_parameters.AddMissingParameters(forwarded_parameters)

        return output


    @classmethod
    def __MakeTransformOperators(cls,
                                 parameters: KratosMultiphysics.Parameters,
                                 data_communicator: KratosMultiphysics.DataCommunicator,
                                 verbosity: int = 2) -> "dict[str,CoSimulationDataTransferOperator]":
        """ @brief Define dataset transform operators.
            @returns A map associating operator names to their associated @ref CoSimulationDataTransferOperator instances.
        """
        return CreateDataTransferOperators(parameters,
                                           data_communicator,
                                           verbosity)


    @classmethod
    def __MakeCouplingSequence(cls,
                               datasets: "dict[str,CouplingInterfaceData]",
                               transform_operators: "dict[str,CoSimulationDataTransferOperator]",
                               parameters: KratosMultiphysics.Parameters) -> "list[CouplingSequenceItem]":
        output: "list[CouplingSequenceItem]" = []
        for item in parameters.values():
            # Each item is expected in the following format:
            #{
            #    "source_dataset" : "",
            #    "transform" : {
            #        "operator" : "",
            #        "parameters" : {}
            #    },
            #    "target_dataset" : ""
            #}
            output.append(CouplingSequenceItem(
                datasets[item["source_dataset"].GetString()],
                transform_operators[item["transform"]["operator"].GetString()],
                item["transform"]["parameters"],
                datasets[item["target_dataset"].GetString()]
            ))
        return output


    ## @}


## @}
## @}
