""" @author Máté Kelemen"""

__all__ = [
    "DatasetTransform",
    "MappedDatasetTransform",
    "SymmetricMappedDatasetTransform",
#    "AcceleratorDatasetTransform"
]

# --- Core Imports ---
import KratosMultiphysics

# --- Mapping Imports ---
import KratosMultiphysics.MappingApplication

# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp

# --- STD Imports ---
import abc


class DatasetTransform(WRApp.WRAppClass, KratosMultiphysics.Operation):
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
                Example:
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
                The example parameters above configure DatasetTransform to fetch data from the REACTION
                historical variable defined on the nodes of the "FluidInterface" model part, apply no
                transformation on it, and assign it to the TRACTION non-historical variable defined on
                the nodes of the "SolidInterface" model part (assignment must be implmented in derived
                classes).
    """

    _expression_map = {
        "nodal_historical"  : {"container_type" : KratosMultiphysics.Expression.ContainerType.NodalHistorical,
                               "expression_type" : KratosMultiphysics.Expression.NodalExpression},
        "nodal"             : {"container_type" : KratosMultiphysics.Expression.ContainerType.NodalNonHistorical,
                               "expression_type" : KratosMultiphysics.Expression.NodalExpression},
        "element"           : {"container_type" : KratosMultiphysics.Expression.ContainerType.ElementNonHistorical,
                               "expression_type" : KratosMultiphysics.Expression.ElementExpression},
        "condition"         : {"container_type" : KratosMultiphysics.Expression.ContainerType.ConditionNonHistorical,
                               "expression_type" : KratosMultiphysics.Expression.ConditionExpression},
    }

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        WRApp.WRAppClass.__init__(self)
        KratosMultiphysics.Operation.__init__(self)

        # Check input
        self._parameters = parameters
        self._parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())
        self.__CheckInputParameters()

        # Get model parts
        self._source_model_part = model.GetModelPart(self._parameters["source"]["model_part_name"].GetString())
        self._target_model_part = model.GetModelPart(self._parameters["target"]["model_part_name"].GetString())


    def Execute(self) -> None:
        for source_params, target_params in zip(self._parameters["source"]["variables"].values(), self._parameters["target"]["variables"].values()):
            source_traits = self._expression_map[source_params["entity_type"].GetString()]
            source_expression = source_traits["expression_type"](self._source_model_part)
            source_variable = KratosMultiphysics.KratosGlobals.GetVariable(source_params["variable_name"].GetString())

            # Populate source expression
            is_historical = source_traits["container_type"] == KratosMultiphysics.Expression.ContainerType.NodalHistorical
            if is_historical or source_traits["container_type"] == KratosMultiphysics.Expression.ContainerType.NodalNonHistorical:
                KratosMultiphysics.Expression.VariableExpressionIO.Read(source_expression, source_variable, is_historical)
            else:
                KratosMultiphysics.Expression.VariableExpressionIO.Read(source_expression, source_variable)

            self._Transform(source_expression, target_params)


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters("""{
            "source" : {
                "model_part_name" : "",
                "variables" : []
            },
            "target" : {
                "model_part_name" : "",
                "variables" : []
            }
        }""")


    @abc.abstractmethod
    def _Transform(self,
                   source_expression,
                   target_params: KratosMultiphysics.Parameters) -> None:
        """ @brief Transform the source expression and apply it to the target variable in the target model part."""
        pass


    def __CheckInputParameters(self) -> None:
        # List of target variables must be unique
        target_variable_names: "set[tuple[str,str]]" = set()
        for target_parameters in self._parameters["target"]["variables"].values():
            target_variable_name = target_parameters["variable_name"].GetString()
            if target_variable_name in target_variable_names:
                raise ValueError(f"Duplicate variable {target_variable_name} in list of target variables\n{self._parameters['target']['variables']}")
            else:
                target_variable_names.add(target_variable_name)


class MappedDatasetTransform(DatasetTransform):
    """ @brief Fetch, transform and assign data between @ref ModelPart s.
        @classname MappedDatasetTransform
        @details This operation consists of 3 subtasks:
                 1) Fetch variables from the source @ref ModelPart.
                 2) Transform fetched data.
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
                    "mapper" : {},                  // <== parameters passed to the mapper factory
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
                Example:
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
                    "mapper" : {
                        "mapper_type" : "nearest_element",
                        "use_initial_configuration" : true
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
                The example parameters above configure DatasetTransform to fetch data from the REACTION
                historical variable defined on the nodes of the "FluidInterface" model part, apply no
                transformation on it, and assign it to the TRACTION non-historical variable defined on
                the nodes of the "SolidInterface" model part.
    """


    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        super().__init__(model, parameters)
        self.__CheckInputParameters()

        # Construct mapper
        is_distributed = self._source_model_part.GetCommunicator().GetDataCommunicator().IsDistributed()
        if is_distributed != self._target_model_part.GetCommunicator().GetDataCommunicator().IsDistributed():
            raise RuntimeError(f"Inconsistent communicators: source {self._source_model_part.GetCommunicator()}, target: {self._target_model_part.GetCommunicator()}")

        if is_distributed:
            from KratosMultiphysics.MappingApplication import MPIExtension as MPIMapping
            mapping_factory = MPIMapping.MPIMapperFactory
        else:
            mapping_factory = KratosMultiphysics.MapperFactory
        self._mapper: KratosMultiphysics.Mapper = mapping_factory.CreateMapper(self._source_model_part,
                                                                               self._target_model_part,
                                                                               self._parameters["mapper"])


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        output = super().GetDefaultParameters()
        output.AddValue("mapper", KratosMultiphysics.Parameters())
        return output


    def _Transform(self,
                   source_expression,
                   target_params: KratosMultiphysics.Parameters) -> None:
        """ @brief Map the source expression to the target variable."""
        target_variable = KratosMultiphysics.KratosGlobals.GetVariable(target_params["variable_name"].GetString())
        target_traits = self._expression_map[target_params["entity_type"].GetString()]

        mapping_flags = KratosMultiphysics.Flags()
        if target_traits["container_type"] == KratosMultiphysics.Expression.ContainerType.NodalNonHistorical:
            mapping_flags |= KratosMultiphysics.Mapper.TO_NON_HISTORICAL

        self._mapper.Map(source_expression.GetExpression(), target_variable, mapping_flags)


    def __CheckInputParameters(self) -> None:
        # Each source expression is associated with exactly one target variable
        if len(self._parameters["source"]["variables"].values()) != len(self._parameters["target"]["variables"].values()):
            raise ValueError(f"Size mismatch between source and target variables:{self._parameters}")

        # Target variables must be defined on nodes
        for target_params in self._parameters["target"]["variables"].values():
            target_container = self._expression_map[target_params["entity_type"].GetString()]["container_type"]
            if target_container not in (KratosMultiphysics.Expression.ContainerType.NodalHistorical, KratosMultiphysics.Expression.ContainerType.NodalNonHistorical):
                raise ValueError(f"Unsupported target \"{target_params['entity_type'].GetString()}\" in {self._parameters}")



class SymmetricMappedDatasetTransform(MappedDatasetTransform):
    """ @brief Fetch, swap signs, and map a variable from a source model part to a target.
        @classname SymmetricMappedDatasetTransform
        @see MappedDatasetTransform
    """

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters) -> None:
        super().__init__(model, parameters)


    def _Transform(self,
                   source_expression,
                   target_params: KratosMultiphysics.Parameters) -> None:
        source_expression *= -1.0
        super()._Transform(source_expression, target_params)

