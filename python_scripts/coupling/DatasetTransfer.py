""" @author Máté Kelemen"""

__all__ = [
    "DatasetTransform",
    "NoOpDatasetTransform",
    "DatasetMap",
    "DatasetLookup"
]

# --- Core Imports ---
import KratosMultiphysics

# --- Mapping Imports ---
import KratosMultiphysics.MappingApplication

# --- WRApp Imports ---
import KratosMultiphysics.WRApplication as WRApp
from ..ToDoException import ToDoException

# --- STD Imports ---
import abc
import typing
import enum



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



class DatasetTable:
    """ @brief
        @classname DatasetTable
    """

    def __init__(self, dataset: "WRApp.Dataset"):
        super().__init__()
        self.__dataset = dataset
        self.__samples: "list[tuple[float,KratosMultiphysics.Expression.Expression]]" = []


    def AddSample(self, argument: float) -> None:
        """ @brief Save the current state of the stored dataset and associate it with the provided argument."""
        range_index = self._GetRangeIndex(argument)
        self.__dataset.Fetch()
        if range_index is None:
            self.__samples = [(argument, self.__dataset.expression)] + self.__samples
        else:
            if argument == self.__samples[range_index][0]: # Don't duplicate entries, overwrite them instead
                self.__samples[range_index] = (argument, self.__dataset.expression)
            else:
                self.__samples.insert(range_index + 1, (argument, self.__dataset.expression))


    def Interpolate(self, argument: float, interpolation: "DatasetTable.Interpolation") -> KratosMultiphysics.Expression.Expression:
        if interpolation == DatasetTable.Interpolation.NEAREST:
            raise ToDoException(f"${interpolation.name} is not implemented yet")
        elif interpolation == DatasetTable.Interpolation.LINEAR:
            range_index = self._GetRangeIndex(argument)
            if range_index is None or (len(self.__samples) - range_index) <= 1:
                raise ValueError(f"No stored range contains samples at {argument}")
            else:
                left = self.__samples[range_index]
                right = self.__samples[range_index + 1]
                return left[1] + (right[1] - left[1]) * (argument - left[0]) * (1 / (right[0] - left[0]))
        else:
            raise ToDoException(f"${interpolation.name} is not implemented yet")


    def Erase(self, predicate: typing.Callable[[float],bool]) -> None:
        self.__samples = [pair for pair in self.__samples if not predicate(pair[0])]


    @property
    def _dataset(self) -> "WRApp.Dataset":
        return self.__dataset


    def _GetRangeIndex(self, argument: float) -> typing.Optional[int]:
        """ @brief Return the index of the entry with the highest sample still smaller than the input argument.
            @details Does a linear search in reverse.
            @todo implement a binary search.
        """
        for reverse_index, pair in enumerate(self.__samples[::-1]):
            if argument <= pair[0]:
                return len(self.__samples) - reverse_index
        return None


    class Interpolation(enum.Enum):
        NEAREST = 0
        LINEAR = 1



class DatasetLookup(DatasetTransform):
    """ @brief Store, retrieve, and interpolate datasets.
        @classname DatasetLookup
        @details This transform expects exactly one @ref CachedDataset
                 as source and exactly one target dataset.
    """

    __dataset_tables: "dict[str,DatasetTable]" = {}


    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        super().__init__(model, parameters)
        self.__interpolation_type = DatasetTable.Interpolation[
            KratosMultiphysics.StringUtilities.ConvertSnakeCaseToCamelCase(parameters["interpolation"].GetString())]
        self.__model_part = model.GetModelPart(parameters["model_part_name"].GetString())

        # Check datasets
        if len(self._datasets) != 1:
            raise ValueError(f"DatasetLookup expects exactly 1 pair of datasets, but got {len(self._datasets)}")

        if not isinstance(self._datasets[0][0], WRApp.CachedDataset):
            raise TypeError(f"The source dataset of DatasetLookup must be a CachedDataset, but got a(n) {type(self._datasets[0][0].__name__)}")


    def Execute(self) -> None:
        time = self.__model_part.ProcessInfo[KratosMultiphysics.TIME]
        self._datasets[0][1].expression = self.__dataset_tables[str(self._datasets[0][0])].Interpolate(
            time,
            self.__interpolation_type)


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        output = super().GetDefaultParameters()
        output["transform"] = KratosMultiphysics.Parameters("""{
            "interpolation" : "nearest_neighbor",
            "model_part_name" : ""
        }""")


    @classmethod
    def __AddSample(cls, dataset: "WRApp.Dataset", argument: float) -> None:
        cls.__datasets.setdefault(str(dataset), WRApp.DatasetTable(dataset)).AddSample(argument)


    @classmethod
    def __Interpolate(cls,
                      dataset: "WRApp.Dataset",
                      argument: float,
                      interpolation: "WRApp.DatasetTable.Interpolation") -> KratosMultiphysics.Expression.Expression:
        return cls.__datasets[str(dataset)].Interpolate(argument, interpolation)


    @classmethod
    def __Erase(cls, dataset: "WRApp.Dataset", predicate: typing.Callable[[float],bool]) -> None:
        cls.__datasets.setdefault(str(dataset), WRApp.DatasetTable(dataset)).Erase(predicate)

