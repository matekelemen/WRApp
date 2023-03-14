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
from KratosMultiphysics.CoSimulationApplication.convergence_criteria.convergence_criteria_wrapper import ConvergenceCriteriaWrapper
from KratosMultiphysics.CoSimulationApplication.convergence_accelerators.convergence_accelerator_wrapper import ConvergenceAcceleratorWrapper

# --- WRApp Imports ---
from .SolutionStageScope import SolutionStageScope
from .AsyncSolver import AsyncSolver
from ..ToDoException import ToDoException
import KratosMultiphysics.WRApplication as WRApp

# --- STD Imports ---
import io
import typing


## @addtogroup WRApplication
## @{
## @addtogroup AsyncAnalysis
## @{


class DatasetTransfer(KratosMultiphysics.Operation):
    """ @brief Class wrapping a dataset fetch-transform-write task in a @ref KratosMultiphysics.Operation.
        @classname DatasetTransfer
        @details Default parameters:
                 @code
                 {
                    "source" : {
                        "partition" : "",   // <== name of the partition to fetch the dataset from
                        "dataset" : ""      // <== name of the dataset to fetch
                    },
                    "transform" : {
                        "operator" : "",    // <== name of the dataset transform/transfer operator (defined in "transform_operators")
                        "parameters" : {}   // <== parameters to pass on the operator
                    },
                    "target" : {
                        "partition" : "",   // <== name of the partition to map the transformed dataset to
                        "dataset" : ""      // <== name of the dataset to map to
                    }
                 }
                 @endcode
    """

    def __init__(self,
                 datasets: "dict[str,CouplingInterfaceData]",
                 transform_operators: "dict[str,CoSimulationDataTransferOperator]",
                 parameters: KratosMultiphysics.Parameters):
        super().__init__()
        parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())
        self.__source_partition_name = parameters["source"]["partition"].GetString()
        self.__source_dataset_name = parameters["source"]["dataset"].GetString()
        self.__source_dataset = datasets[self.__source_dataset_name]

        self.__transformation_name = parameters["transform"]["operator"].GetString()
        self.__transformation = transform_operators[self.__transformation_name]
        self.__transformation_parameters = parameters["transform"]["parameters"]

        self.__target_partition_name = parameters["target"]["partition"].GetString()
        self.__target_dataset_name = parameters["target"]["dataset"].GetString()
        self.__target_dataset = datasets[self.__target_dataset_name]


    def Execute(self) -> None:
        self.__transformation.TransferData(self.__source_dataset,
                                           self.__target_dataset,
                                           self.__transformation_parameters)


    def WriteInfo(self, stream: io.StringIO, prefix: str = "") -> None:
        stream.write(f"{prefix}fetch dataset '{self.__source_dataset_name}' from partition '{self.__source_partition_name}'\n")
        stream.write(f"{prefix}apply transformation '{self.__transformation_name}'\n")
        stream.write(f"{prefix}write transformed data to dataset '{self.__target_dataset_name}' in partition '{self.__target_partition_name}'\n")


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        """ @details @code
                     {
                        "source" : {
                            "partition" : "",   // <== name of the partition to fetch the dataset from
                            "dataset" : ""      // <== name of the dataset to fetch
                        },
                        "transform" : {
                            "operator" : "",    // <== name of the dataset transform/transfer operator (defined in "transform_operators")
                            "parameters" : {}   // <== parameters to pass on the operator
                        },
                        "target" : {
                            "partition" : "",   // <== name of the partition to map the transformed dataset to
                            "dataset" : ""      // <== name of the dataset to map to
                        }
                     }
                     @endcode
        """
        return KratosMultiphysics.Parameters(R"""{
            "source" : {
                "partition" : "",
                "dataset" : ""
            },
            "transform" : {
                "operator" : "",
                "parameters" : {}
            },
            "target" : {
                "partition" : "",
                "dataset" : ""
            }
        }""")



class SubSynchronization(KratosMultiphysics.Operation):
    """ @brief A class wrapping @ref AsnycSolver._Synchronize in a @ref KratosMultiphysics.Operation.
        @classname SubSynchronization
        @details This operation is meant to be executed as part of the coupling sequence of
                 @ref CoSimCoupling, in between calls to @ref DatasetTransfer operations.
        @details Default parameters:
                 @code
                 {
                    "partition" : "" // <== partition to synchronize
                 }
                 @endcode
    """

    def __init__(self,
                 partition_name: str,
                 solver: AsyncSolver):
        super().__init__()
        self.__partition_name = partition_name
        self.__solver = solver


    def Execute(self) -> None:
        with self.__solver.Synchronize() as synchronize:
            synchronize()


    def WriteInfo(self, stream: io.StringIO, prefix: str = "") -> None:
        stream.write(f"{prefix}synchronize partition '{self.__partition_name}'\n")


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters(R"""{
            "partition" : ""    // <== name of the partition to synchronize
        }""")



class CoSimCoupling(SolutionStageScope, WRApp.WRAppClass):
    """ @brief Wrapper for CoSimulationApplication coupling procedures.
        @classname CoSimCoupling
        @details Default parameters:
                 @code
                 {
                    "interface_datasets" : [],
                    "transform_operators" : {},
                    "coupling_sequence" : [],
                    "convergence_accelerators" : [],
                    "convergence_criteria" : [],
                    "max_iterations" : 0
                    "verbosity" : 2
                 }
                 @endcode
                 @a "transform_operators" is forwarded to @ref CoSimulationApplication.factories.helpers.CreateDataTransferOperators.
                 @a "coupling_operations" is forwarded to CoSimulationApplication.factories.helpers.CreateCouplingOperations.
        @details Items in @a "interface_datasets" represent exposed sets of data on partition interfaces. The expected format
                 of each item:
                 @code
                 {
                    "name" : "",            // <== name of the dataset
                    "partition" : "",       // <== name of related partition
                    "model_part_name" : "", // <== name of the ModelPart within the partition the dataset is defined on
                    "dimension" : 0,        // <== number of components in each item of the dataset
                    "variable_name" : ""    // <== name of the variable the dataset refers to
                 }
                 @endcode
        @details Each item in @a "coupling_sequence" either defines a fetch-transform-write operation @ref DatasetTransfer
                 or a subsynchronization (usually a single call to @ref PythonSolver.SolveSolutionStep) @ref SubSynchronization.
                 Each item is expected in the following format:
                 @code
                 {
                    "type" : "",        // <== "trasfer" or "subsync"
                    "parameters" : {}   // <== parameters passed on to the appropriate constructor
                 }
                 @endcode
                 - fetch a specific dataset from a source partition
                 - transform the fetched dataset
                 - write the transformed dataset to a dataset defined in the target partition
    """

    def __init__(self,
                 solver: AsyncSolver,
                 model: KratosMultiphysics.Model,
                 data_communicator: KratosMultiphysics.DataCommunicator,
                 parameters: KratosMultiphysics.Parameters):
        WRApp.WRAppClass.__init__(self)
        parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())
        self.__solver_root = solver
        self.__parameters = parameters
        self.__data_communicator = data_communicator

        self.__max_iterations = parameters["max_iterations"].GetInt()
        self.__verbosity = parameters["verbosity"].GetInt()

        # Define exposed datasets on partition interfaces
        self.__datasets = self.__MakeDatasets(model, self.parameters["interface_datasets"])

        ## @todo Define coupling operators
        if len(self.__parameters["coupling_operations"].items()):
            raise ToDoException('"coupling_operations" are not supported yet')

        # Coupling subiteration utilities
        self.__convergence_criteria = self.__MakeConvergenceCriteria(self.parameters["convergence_criteria"],
                                                                     self.__verbosity)

        for criterion in self.__convergence_criteria:
            criterion.Initialize()

        self.__convergence_accelerators = self.__MakeConvergenceAccelerators(self.parameters["convergence_accelerators"],
                                                                             self.__verbosity)

        for accelerator in self.__convergence_accelerators:
            accelerator.Initialize()

        # Map transform operator names to the operators they represent
        self.__transform_operators = self.__MakeTransformOperators(self.parameters["transform_operators"],
                                                                   self.parameters["verbosity"].GetInt())

        # Create a list of operations that must be executed in order at each synchronization
        self.__coupling_sequence = self.__MakeCouplingSequence(self.parameters["coupling_sequence"])


    def _Preprocess(self) -> None:
        for criterion in self.__convergence_criteria:
            criterion.InitializeSolutionStep()
        for accelerator in self.__convergence_accelerators:
            accelerator.InitializeSolutionStep()


    def __call__(self) -> None:
        """ @brief Execute all items in the coupling sequence in the order they were defined."""
        for i_couple in range(self.__max_iterations):
            # Coupling subiter utils preproc
            for accelerator in self.__convergence_accelerators:
                accelerator.InitializeNonLinearIteration()
            for criterion in self.__convergence_criteria:
                criterion.InitializeNonLinearIteration()

            # Perform coupling operations in the defined order, consisting of
            # - data transfer between partitions
            # - partition synchronization
            for operation in self.__coupling_sequence:
                operation.Execute()

            # Coupling subiter utils postproc
            for accelerator in self.__convergence_accelerators:
                accelerator.FinalizeNonLinearIteration()
            for criterion in self.__convergence_criteria:
                criterion.FinalizeNonLinearIteration()

            # Exit early if all convergence criteria are satisfied
            if all(criterion.IsConverged() for criterion in self.__convergence_criteria):
                if self.__verbosity:
                    print(f"Coupling converged after {i_couple + 1} iteration{'s' if i_couple else ''}")
                return

            if i_couple + 1 < self.__max_iterations:
                for accelerator in self.__convergence_accelerators:
                    accelerator.ComputeAndApplyUpdate()

        # If the flow reached this point, the coupling failed
        raise RuntimeError(f"Coupling failed to converge in {self.__max_iterations} iterations")


    def _Postprocess(self) -> None:
        for criterion in self.__convergence_criteria:
            criterion.FinalizeSolutionStep()
        for accelerator in self.__convergence_accelerators:
            accelerator.FinalizeSolutionStep()


    def WriteInfo(self, stream: io.StringIO, prefix: str = "") -> None:
        if self.__max_iterations:
            stream.write(f"{prefix}for max {self.__max_iterations} time{'s' if 1 < self.__max_iterations else ''}:\n")
            subprefix = prefix + "|  "
            for item in self.__coupling_sequence:
                item.WriteInfo(stream, subprefix)


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
                "interface_datasets" : [],
                "coupling_operations" : {},
                "transform_operators" : {},
                "coupling_sequence" : [],
                "convergence_accelerators" : [],
                "convergence_criteria" : [],
                "max_iterations" : 0,
                "verbosity" : 2
            }
            @endcode
        """
        return KratosMultiphysics.Parameters(R"""{
            "interface_datasets" : [],
            "coupling_operations" : {},
            "transform_operators" : {},
            "coupling_sequence" : [],
            "convergence_accelerators" : [],
            "convergence_criteria" : [],
            "max_iterations" : 0,
            "verbosity" : 2
        }""")


    @classmethod
    def __MakeDatasets(cls,
                       model: KratosMultiphysics.Model,
                       parameters: KratosMultiphysics.Parameters) -> "dict[str,CouplingInterfaceData]":
        """ @brief Define exposed interface datasets that can later be fetched from / written to.
            @details @a parameters are expected as an array of objects in the following format:
                     @code
                     {
                        "name" : "",
                        "partition" : "",
                        "model_part_name" : "",
                        "dimension" : 0,
                        "variable_name" : ""
                      }
                     @endcode
            @returns A map associating dataset names to their respective @ref CouplingInterfaceData instances.
        """
        output: "dict[str,CouplingInterfaceData]" = {}
        for dataset_parameters in parameters.values():
            dataset_name = dataset_parameters["name"].GetString()
            partition_name = dataset_parameters["partition"].GetString()

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


    def __MakeConvergenceCriteria(self,
                                  parameters: KratosMultiphysics.Parameters,
                                  verbosity: int) -> "list[ConvergenceCriteriaWrapper]":
        output: "list[ConvergenceCriteriaWrapper]" = []
        for criterion_parameters in parameters.values():
            dataset = self.__datasets[criterion_parameters["data_name"].GetString()]
            if not criterion_parameters.Has("echo_level"):
                criterion_parameters.AddInt("echo_level", verbosity)
            output.append(ConvergenceCriteriaWrapper(criterion_parameters,
                                                     dataset,
                                                     self.__data_communicator))
        return output


    def __MakeConvergenceAccelerators(self,
                                      parameters: KratosMultiphysics.Parameters,
                                      verbosity: int) -> "list[ConvergenceAcceleratorWrapper]":
        output: "list[ConvergenceAcceleratorWrapper]" = []
        for accelerator_parameters in parameters.values():
            if not accelerator_parameters.Has("echo_level"):
                accelerator_parameters.AddInt("echo_level", verbosity)
            output.append(ConvergenceAcceleratorWrapper(accelerator_parameters,
                                                        self.__datasets,
                                                        self.__data_communicator))
        return output


    def __MakeTransformOperators(self,
                                 parameters: KratosMultiphysics.Parameters,
                                 verbosity: int = 2) -> "dict[str,CoSimulationDataTransferOperator]":
        """ @brief Define dataset transform operators.
            @returns A map associating operator names to their associated @ref CoSimulationDataTransferOperator instances.
        """
        return CreateDataTransferOperators(parameters,
                                           self.__data_communicator,
                                           verbosity)


    def __MakeCouplingSequence(self, parameters: KratosMultiphysics.Parameters) -> "list[typing.Union[DatasetTransfer,SubSynchronization]]":
        """ @brief Construct a list of objects responsible for data fetching, transform, and writing between partitions.
            @details The input @a parameters is expected as a list of objects in the following format:
                     @code
                     {
                        "type" : "",        // <== "transfer" or "subsync"
                        "parameters" : {}   // <== parameters passed on to DatasetTransfer or SubSynchronization
                     }
                     @endcode
                     Each item represents either a @ref DatasetTransfer or a @ref SubSynchronization.
        """
        output: "list[typing.Union[DatasetTransfer,SubSynchronization]]" = []
        for item in parameters.values():
            coupling_item_type = item["type"].GetString()
            if coupling_item_type == "transfer":
                output.append(DatasetTransfer(
                    self.__datasets,
                    self.__transform_operators,
                    item["parameters"]
                ))
            elif coupling_item_type == "subsync":
                partition_name = item["parameters"]["partition"].GetString()
                output.append(SubSynchronization(
                    partition_name,
                    self.__solver_root.GetSolver(partition_name)
                ))
        return output


    ## @}


## @}
## @}
