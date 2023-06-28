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


_EXPRESSION_MAP = {
    "nodal_historical"  : {"container_type" : KratosMultiphysics.Expression.ContainerType.NodalHistorical,
                           "expression_type" : KratosMultiphysics.Expression.NodalExpression},
    "nodal"             : {"container_type" : KratosMultiphysics.Expression.ContainerType.NodalNonHistorical,
                           "expression_type" : KratosMultiphysics.Expression.NodalExpression},
    "element"           : {"container_type" : KratosMultiphysics.Expression.ContainerType.ElementNonHistorical,
                           "expression_type" : KratosMultiphysics.Expression.ElementExpression},
    "condition"         : {"container_type" : KratosMultiphysics.Expression.ContainerType.ConditionNonHistorical,
                           "expression_type" : KratosMultiphysics.Expression.ConditionExpression}
}



class DatasetTransform(WRApp.WRAppClass, abc.ABC):
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
                    "source" : {
                        "model_part_name" : "",     // <== name of the ModelPart to fetch the dataset from
                        "variables" : []            // <== list of variables to fetch
                    },
                    "transform" : {},               // <== transform parameters (required by derived classes)
                    "target" : {
                        "model_part_name" : "",     // <== name of the ModelPart to assign the datasets to
                        "variables" : []            // <== list of variables to assign to
                    }
                 }
                 @endcode

                Source and target variables can be defined in the same manner, specifying the entity
                types they belong to ("nodal_historical", "nodal", "element", or "condition") and the
                name of the variable. The number of source and target variables must be equal, as each
                transformed source dataset is assigned to the target dataset at the matching position.
                Example for @ref DatasetMap:
                @code
                {
                    "source" : {
                        "model_part_name" : "FluidInterface",
                        "variables" : [
                            {
                                "entity_type" : "nodal_historical",
                                "variable_name" : "REACTION"
                            }
                        ]
                    },
                    "transform" : {
                        "mapper_parameters" : {
                            "mapper_type" : "nearest_neighbor"
                        }
                        "swap_signs" : true
                    },
                    "target" : {
                        "model_part_name" : "SolidInterface",
                        "variables" : [
                            {
                                "entity_type" : "nodal",
                                "variable_name" : "TRACTION"
                            }
                        ] // "variables"
                    } // "target"
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
        super().__init__()
        default_parameters = self.GetDefaultParameters()
        parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())

        self.__source_parameters = parameters["source"]
        self.__target_parameters = parameters["target"]
        self.__transform_parameters = parameters["transform"]

        self.__source_parameters.ValidateAndAssignDefaults(default_parameters["source"])
        self.__target_parameters.ValidateAndAssignDefaults(default_parameters["target"])
        self.__transform_parameters.ValidateAndAssignDefaults(default_parameters["transform"])

    @abc.abstractmethod
    def __call__(self) -> None:
        pass


    @classmethod
    def Factory(cls,
                model: KratosMultiphysics.Model,
                parameters: KratosMultiphysics.Parameters) -> "DatasetTransform":
        """ @brief Factory function creating a @ref DatasetTransform from a set of standard arguments.
            @details Derived classes with non-standard constructors must override this function.
        """
        return cls(model, parameters)


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters("""{
            "source" : {
                "model_part_name" : "",
                "variables" : []
            },
            "transform" : {},
            "target" : {
                "model_part_name" : "",
                "variables" : []
            }
        }""")


    @property
    def _source_parameters(self) -> KratosMultiphysics.Parameters:
        return self.__source_parameters


    @property
    def _target_parameters(self) -> KratosMultiphysics.Parameters:
        return self.__target_parameters


    @property
    def _transform_parameters(self) -> KratosMultiphysics.Parameters:
        return self.__transform_parameters



class NoOpDatasetTransform(DatasetTransform):
    """ @brief @a DatasetTransform that directly assigns fetched datasets without doing anything to them.
        @classname NoOpDatasetTransform
    """

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        super().__init__(model, parameters)


    def __call__(self) -> None:
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
                    "source" : {
                        "model_part_name" : "",     // <== name of the ModelPart to fetch the dataset from
                        "variables" : []            // <== list of variables to fetch
                    },
                    "transform" : {
                        "mapper_parameters" : {},   // <== parameters passed on to the mapper factory
                        "swap_signs" : false        // <== indicates whether to swap signs before assigning the target dataset
                    },
                    "target" : {
                        "model_part_name" : "",     // <== name of the ModelPart to assign the datasets to
                        "variables" : []            // <== list of variables to assign to
                    }
                 }
                 @endcode

                Source and target variables can be defined in the same manner, specifying the entity
                types they belong to ("nodal_historical", "nodal", "element", or "condition") and the
                name of the variable. The number of source and target variables must be equal, as each
                transformed source dataset is assigned to the target dataset at the matching position.
                Example for @ref DatasetMap:
                @code
                {
                    "source" : {
                        "model_part_name" : "FluidInterface",
                        "variables" : [
                            {
                                "entity_type" : "nodal_historical",
                                "variable_name" : "REACTION"
                            }
                        ]
                    },
                    "transform" : {
                        "mapper_parameters" : {
                            "mapper_type" : "nearest_neighbor"
                        }
                        "swap_signs" : true
                    },
                    "target" : {
                        "model_part_name" : "SolidInterface",
                        "variables" : [
                            {
                                "entity_type" : "nodal",
                                "variable_name" : "TRACTION"
                            }
                        ] // "variables"
                    } // "target"
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
        self.__mapped_structs: "list[DatasetMap.__MappedStruct]" = []
        self.__mapper = mapper

        source_model_part = model.GetModelPart(self._source_parameters["model_part_name"].GetString())
        target_model_part = model.GetModelPart(self._target_parameters["model_part_name"].GetString())

        # Check whether redundant inputs are consistent
        # => model parts are specified by the input model + parameters combos
        #    but the mapper must already have the source and target model parts too.
        #if source_model_part.Name != mapper.GetInterfaceModelPartOrigin().Name:
        #    raise RuntimeError(f"Source model part mismatch: {source_model_part.Name} != {mapper.GetInterfaceModelPartOrigin().Name}")
        #if target_model_part.Name != mapper.GetInterfaceModelPartDestination().Name:
        #    raise RuntimeError(f"Target model part mismatch: {target_model_part.Name} != {mapper.GetInterfaceModelPartDestination().Name}")

        # Check input variables
        if len(self._source_parameters["variables"].values()) != len(self._target_parameters["variables"].values()):
            raise ValueError(f"Number of source and target variables must match: {len(self._source_parameters['variables'].values())} sources, {len(self._target_parameters['variables'].values())} targets")

        common_mapper_flags = KratosMultiphysics.Flags()
        if self._transform_parameters["swap_signs"].GetBool():
            common_mapper_flags |= KratosMultiphysics.Mapper.SWAP_SIGN

        for source, target in zip(self._source_parameters["variables"].values(), self._target_parameters["variables"].values()):
            source_traits = _EXPRESSION_MAP[source["entity_type"].GetString()]
            target_traits = _EXPRESSION_MAP[target["entity_type"].GetString()]

            # Mapping between elements or conditions is not supported
            for entry, location in zip((source_traits, target_traits), ("source", "target")):
                if entry["container_type"] == KratosMultiphysics.Expression.ContainerType.ElementNonHistorical:
                    raise ValueError(f"Mapping {'from' if location == 'source' else 'to'} elements is not supported")
                if entry["container_type"] == KratosMultiphysics.Expression.ContainerType.ConditionNonHistorical:
                    raise ValueError(f"Mapping {'from' if location == 'source' else 'to'} conditions is not supported")

            self.__mapped_structs.append(DatasetMap.__MappedStruct(
                KratosMultiphysics.Expression.NodalExpression(source_model_part),
                KratosMultiphysics.KratosGlobals.GetVariable(source["variable_name"].GetString()),
                source_traits["container_type"] == KratosMultiphysics.Expression.ContainerType.NodalHistorical,
                target_model_part,
                KratosMultiphysics.KratosGlobals.GetVariable(target["variable_name"].GetString()),
                target_traits["container_type"] == KratosMultiphysics.Expression.ContainerType.NodalHistorical,
                common_mapper_flags))


    def __call__(self) -> None:
        for mapped_struct in self.__mapped_structs:
            mapped_struct.Map(self.__mapper)


    @classmethod
    def Factory(cls,
                model: KratosMultiphysics.Model,
                parameters: KratosMultiphysics.Parameters) -> "DatasetMap":
        """ @brief Construct a @ref DatasetMap and its related @ref Mapper."""
        # Construct the mapper
        source_model_part = model.GetModelPart(parameters["source"]["model_part_name"].GetString())
        target_model_part = model.GetModelPart(parameters["target"]["model_part_name"].GetString())
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
        return cls(model,
                   parameters,
                   mapper_factory.CreateMapper(source_model_part, target_model_part, parameters["transform"]["mapper_parameters"]))


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters("""{
            "source" : {
                "model_part_name" : "",
                "variables" : []
            },
            "transform" : {
                "mapper_parameters" : {},
                "swap_signs" : false
            },
            "target" : {
                "model_part_name" : "",
                "variables" : []
            }
        }""")


    class __MappedStruct:
        """ @brief Utility struct for mapping a single dataset pair."""

        def __init__(self,
                     source_expression: KratosMultiphysics.Expression.NodalExpression,
                     source_variable: WRApp.Typing.Variable,
                     source_is_historical: bool,
                     target_model_part: KratosMultiphysics.ModelPart,
                     target_variable: WRApp.Typing.Variable,
                     target_is_historical: bool,
                     mapper_flags: KratosMultiphysics.Flags):
            self.__source_expression = source_expression
            self.__source_variable = source_variable
            self.__source_is_historical = source_is_historical
            self.__target_model_part = target_model_part
            self.__target_variable = target_variable
            self.__target_is_historical = target_is_historical
            self.__mapper_flags = mapper_flags


        def Map(self, mapper: KratosMultiphysics.Mapper) -> None:
            KratosMultiphysics.Expression.VariableExpressionIO.Read(self.__source_expression,
                                                                    self.__source_variable,
                                                                    self.__source_is_historical)
            target_expression = KratosMultiphysics.Expression.NodalExpression(self.__target_model_part)
            target_expression.SetExpression(mapper.Map(self.__source_expression.GetExpression(), self.__mapper_flags))
            KratosMultiphysics.Expression.VariableExpressionIO.Write(target_expression,
                                                                     self.__target_variable,
                                                                     self.__target_is_historical)
