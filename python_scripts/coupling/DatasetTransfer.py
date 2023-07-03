""" @author Máté Kelemen"""

__all__ = [
    "DatasetTransform",
    "NoOpDatasetTransform",
    "DatasetMap"
]

# --- Core Imports ---
import KratosMultiphysics

# --- Mapping Imports ---
import KratosMultiphysics.MappingApplication

# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp

# --- STD Imports ---
import abc



class DatasetTransform(WRApp.WRAppClass, KratosMultiphysics.Operation, abc.ABC):
    """ @brief Fetch, transform and assign data between @ref ModelPart s.
        @classname DatasetTransform
        @details This operation consists of 3 subtasks:
                 1) Fetch variables from the source @ref ModelPart.
                 2) Transform fetched data (implemented by derived classes).
                 3) Assign the transformed data to the target @ref ModelPart.

                 Fetching and assigning data can only be performed on variables,
                 but the source and target variables need not be the same variable,
                 or even be defined on the same entity types.

                 Default parameters:
                 @code
                 {
                    "source" : [],    // <== source datasets
                    "transform" : {}, // <== transform parameters (required by derived classes)
                    "targets" : []    // <== target datasets
                 }
                 @endcode

                Source and target variables can be defined in the same manner, specifying the entity
                types they belong to ("nodal_historical", "nodal", "element", or "condition") and the
                name of the variable. The number of source and target variables must be equal, as each
                transformed source dataset is assigned to the target dataset at the matching position.
                Example for @ref DatasetMap:
                @code
                {
                    "sources" : [
                        {
                            "model_part_name" : "SolidInterface",
                            "container_type" : "nodal_historical",
                            "variable_name" : "REACTION"
                        }
                    ],
                    "transform" : {
                        "mapper_parameters" : {
                            "mapper_type" : "nearest_neighbor"
                        }
                        "swap_signs" : true
                    },
                    "targets" : [
                            {
                                "model_part_name" : "SolidInterface",
                                "container_type" : "nodal",
                                "variable_name" : "TRACTION"
                            }
                    ] // "targets"
                }
                @endcode
                The example parameters above configure @ref DatasetMap to fetch data from the @a REACTION
                historical variable defined on the nodes of the "FluidInterface" model part, maps it to
                the nearest neighbour in the target model part, and assign it to the @a TRACTION non-historical
                variable defined on the nodes of the "SolidInterface" model part.
    """

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        WRApp.WRAppClass.__init__(self)
        KratosMultiphysics.Operation.__init__(self)
        abc.ABC.__init__(self)
        default_parameters = self.GetDefaultParameters()
        parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())

        self.__transform_parameters = parameters["transform"]
        self.__transform_parameters.ValidateAndAssignDefaults(default_parameters["transform"])

        source_parameters = parameters["sources"]
        target_parameters = parameters["targets"]

        if len(source_parameters.values()) != len(target_parameters.values()):
            raise ValueError(f"Source/target dataset size mismatch: {len(source_parameters.values())} sources, {len(target_parameters.values())} targets")

        self.__datasets: "list[tuple[WRApp.Dataset,WRApp.Dataset]]" = [] # <== {source_dataset, target_dataset}
        for source, target in zip(source_parameters.values(), target_parameters.values()):
            self.__datasets.append((
                WRApp.GetRegisteredClass(source["type"].GetString()).Factory(model, source["parameters"]),
                WRApp.GetRegisteredClass(target["type"].GetString()).Factory(model, target["parameters"])
            ))


    @abc.abstractmethod
    def Execute(self) -> None:
        pass


    @classmethod
    def Factory(cls,
                solver: "WRApp.AsyncSolver",
                parameters: KratosMultiphysics.Parameters) -> "DatasetTransform":
        """ @brief Factory function creating a @ref DatasetTransform from a set of standard arguments.
            @details Derived classes with non-standard constructors must override this function.
        """
        return cls(solver.model, parameters)


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters("""{
            "sources" : [],
            "transform" : {},
            "targets" : []
        }""")


    @property
    def _transform_parameters(self) -> KratosMultiphysics.Parameters:
        return self.__transform_parameters


    @property
    def _datasets(self) -> "list[tuple[WRApp.Dataset,WRApp.Dataset]]":
        return self.__datasets



class NoOpDatasetTransform(DatasetTransform):
    """ @brief @a DatasetTransform that directly assigns fetched datasets without doing anything to them.
        @classname NoOpDatasetTransform
    """

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        super().__init__(model, parameters)


    def Execute(self) -> None:
        pass


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters()



class DatasetMap(DatasetTransform):
    """ @brief @a DatasetTransform that uses a @ref Mapper to map datasets before assigning them to the target @ref ModelPart.
        @classname DatasetMap
        @details This operation consists of 3 subtasks:
                 1) Fetch variables from the source @ref ModelPart.
                 2) Map the fetched data from the source @ref ModelPart to the target @a ModelPart.
                 3) Assign the transformed data to the target @ref ModelPart.

                 Fetching and assigning data can only be performed on variables,
                 but the source and target variables need not be the same variable,
                 or even be defined on the same entity types.

                 Default parameters:
                 @code
                 {
                    "sources" : [],                     // <== source datasets
                    "transform" : {
                        "source_model_part_name" : "",  // <== name of the model part to map from
                        "target_model_part_name" : "",  // <== name of the model part to map to
                        "mapper_parameters" : {},       // <== parameters passed on to the mapper factory
                        "swap_signs" : false            // <== indicates whether to swap signs before assigning the target dataset
                    },
                    "target" : []                       // <== target_datasets
                 }
                 @endcode

                Source and target variables can be defined in the same manner, specifying the entity
                types they belong to ("nodal_historical", "nodal", "element", or "condition") and the
                name of the variable. The number of source and target variables must be equal, as each
                transformed source dataset is assigned to the target dataset at the matching position.
                Example for @ref DatasetMap:
                @code
                {
                    "sources" : [
                        {
                            "model_part_name" : "FluidInterface",
                            "container_type" : "nodal_historical",
                            "variable_name" : "REACTION"
                        }
                    ],
                    "transform" : {
                        "source_model_part_name" : "FluidInterface",
                        "target_model_part_name" : "SolidInterface",
                        "mapper_parameters" : {
                            "mapper_type" : "nearest_neighbor"
                        }
                        "swap_signs" : true
                    },
                    "targets" : [
                            {
                                "model_part_name" : "SolidInterface",
                                "container_type" : "nodal",
                                "variable_name" : "TRACTION"
                            }
                    ] // "targets"
                }
                @endcode
                The example parameters above configure @ref DatasetMap to fetch data from the @a REACTION
                historical variable defined on the nodes of the "FluidInterface" model part, maps it to
                the nearest neighbour in the target model part, and assign it to the @a TRACTION non-historical
                variable defined on the nodes of the "SolidInterface" model part.
    """

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters,
                 mapper: KratosMultiphysics.Mapper):
        super().__init__(model, parameters)
        self.__mapper = mapper
        self.__mapper_flags = KratosMultiphysics.Flags()
        if self._transform_parameters["swap_signs"].GetBool():
            self.__mapper_flags |= KratosMultiphysics.Mapper.SWAP_SIGN


    def Execute(self) -> None:
        for dataset_pair in self._datasets:
            dataset_pair[0].Fetch()
            dataset_pair[1].expression = self.__mapper.Map(dataset_pair[0].expression,
                                                           self.__mapper_flags)
            dataset_pair[1].Assign()


    @classmethod
    def Factory(cls,
                solver: "WRApp.AsyncSolver",
                parameters: KratosMultiphysics.Parameters) -> "DatasetMap":
        """ @brief Construct a @ref DatasetMap and its related @ref Mapper."""
        # Make sure the required keys exist
        default_parameters = cls.GetDefaultParameters()
        parameters.ValidateAndAssignDefaults(default_parameters)
        transform_parameters = parameters["transform"]
        transform_parameters.ValidateAndAssignDefaults(default_parameters["transform"])

        # Construct the mapper
        source_model_part = solver.model.GetModelPart(transform_parameters["source_model_part_name"].GetString())
        target_model_part = solver.model.GetModelPart(transform_parameters["target_model_part_name"].GetString())
        source_is_distributed = source_model_part.GetCommunicator().GetDataCommunicator().IsDistributed()
        target_is_distributed = target_model_part.GetCommunicator().GetDataCommunicator().IsDistributed()

        if all((source_is_distributed, target_is_distributed)):
            from KratosMultiphysics.MappingApplication import MPIExtension as MPIMapping
            mapper_factory = MPIMapping.MPIMapperFactory
        elif not any((source_is_distributed, target_is_distributed)):
            mapper_factory = KratosMultiphysics.MapperFactory
        else:
            raise RuntimeError(f"Source model part is {'' if source_is_distributed else 'not'} distributed, but the the target is {'' if target_is_distributed else 'not'}")

        # Construct DatasetMap
        return cls(solver.model,
                   parameters,
                   mapper_factory.CreateMapper(source_model_part, target_model_part, parameters["transform"]["mapper_parameters"]))


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters("""{
            "sources" : [],
            "transform" : {
                "source_model_part_name" : "",
                "target_model_part_name" : "",
                "mapper_parameters" : {},
                "swap_signs" : false
            },
            "targets" : []
        }""")
