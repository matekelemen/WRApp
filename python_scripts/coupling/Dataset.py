""" @author Máté Kelemen"""

__all__ = [
    "Dataset",
    "KratosDataset"
]

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
from KratosMultiphysics import WRApplication as WRApp

# --- STD Imports ---
import abc


class Dataset(WRApp.WRAppClass):
    """ @brief Class representing a dataset that can be operated on during coupling.
        @classname Dataset
        @details This class has 2 levels of abstraction:
                 1) the dataset interface that consists of @a Fetch and @a Assign
                 2) the expression interface handling data storage and providing an
                    interface to Kratos.

                 The @a Fetch and @a Assign functions must be implemented in derived
                 classes and handle read/write operations from/to their associated
                 storeage respectively. These operations must act on an internally
                 stored @ref Expression that also must be exposed by derived classes
                 through the @a expression property.
    """

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        self.__model = model
        self.__parameters = parameters
        super().__init__()


    @classmethod
    def Factory(cls,
                model: KratosMultiphysics.Model,
                parameters: KratosMultiphysics.Parameters) -> "Dataset":
        return cls(model, parameters)


    @abc.abstractmethod
    def Fetch(self) -> None:
        """ @brief Update the internally stored @ref Expression."""
        pass


    @abc.abstractmethod
    def Assign(self) -> None:
        """ @brief Overwrite the associated storage with the data of the internally stored @ref Expression."""
        pass


    @property
    @abc.abstractmethod
    def expression(self) -> KratosMultiphysics.Expression.Expression:
        """ @brief Provide access to the internally stored @ref Expression."""
        pass


    @expression.setter
    @abc.abstractmethod
    def expression(self, right: KratosMultiphysics.Expression.Expression) -> None:
        """ @brief Overwrite the internally stored @ref Expression."""
        pass


    @property
    def _model(self) -> KratosMultiphysics.Model:
        return self.__model


    @property
    def _parameters(self) -> KratosMultiphysics.Parameters:
        return self.__parameters



class KratosDataset(Dataset):
    """ @brief Class representing a @ref Variable stored in a @ref ModelPart.
        @classname KratosDataset
        @details Default parameters:
                 @code
                 {
                    "model_part_name" : "", // <== full name of the associated model part
                    "container_type" : ""   // <== ["nodal_historical", "nodal", "element", "condition"]
                    "variable_name" : ""    // <== name of the associated variable
                 }
                 @endcode
    """

    def __init__(self,
                 model: KratosMultiphysics.Model,
                 parameters: KratosMultiphysics.Parameters):
        super().__init__(model, parameters)
        parameters.ValidateAndAssignDefaults(self.GetDefaultParameters())
        model_part = self._model.GetModelPart(self._parameters["model_part_name"].GetString())
        self.__container_expression = WRApp.StringMaps.expressions[self._parameters["container_type"].GetString()](model_part)
        self.__variable = KratosMultiphysics.KratosGlobals.GetVariable(self._parameters["variable_name"].GetString())
        self.__is_historical = WRApp.StringMaps.is_historical_container[self._parameters["container_type"].GetString()]


    @classmethod
    def GetDefaultParameters(cls) -> KratosMultiphysics.Parameters:
        return KratosMultiphysics.Parameters("""{
            "model_part_name" : "",
            "container_type" : "",
            "variable_name" : ""
        }""")


    def Fetch(self) -> None:
        if isinstance(self.__container_expression, KratosMultiphysics.Expression.NodalExpression):
            KratosMultiphysics.Expression.VariableExpressionIO.Read(self.__container_expression,
                                                                    self.__variable,
                                                                    self.__is_historical)
        else:
            KratosMultiphysics.Expression.VariableExpressionIO.Read(self.__container_expression,
                                                                    self.__variable)


    def Assign(self) -> None:
        if isinstance(self.__container_expression, KratosMultiphysics.Expression.NodalExpression):
            KratosMultiphysics.Expression.VariableExpressionIO.Write(self.__container_expression,
                                                                     self.__variable,
                                                                     self.__is_historical)
        else:
            KratosMultiphysics.Expression.VariableExpressionIO.Write(self.__container_expression,
                                                                     self.__variable)


    @property
    def expression(self) -> KratosMultiphysics.Expression.Expression:
        return self.__container_expression.GetExpression()


    @expression.setter
    def expression(self, right: KratosMultiphysics.Expression.Expression) -> None:
        self.__container_expression.SetExpression(right)
