""" @author Máté Kelemen"""

__all__ = [
    "StringMaps"
]

# --- Core Imports ---
import KratosMultiphysics

# --- STD Imports ---
import typing


class StringMaps:

    expressions: "dict[str,typing.Union[typing.Type[KratosMultiphysics.Expression.NodalExpression],typing.Type[KratosMultiphysics.Expression.ElementExpression],typing.Type[KratosMultiphysics.Expression.ConditionExpression]]]" = {
        "nodal_historical"  : KratosMultiphysics.Expression.NodalExpression,
        "nodal"             : KratosMultiphysics.Expression.NodalExpression,
        "element"           : KratosMultiphysics.Expression.ElementExpression,
        "condition"         : KratosMultiphysics.Expression.ConditionExpression
    }

    containers: "dict[str,KratosMultiphysics.Expression.ContainerType]" = {
        "nodal_historical"  : KratosMultiphysics.Expression.ContainerType.NodalHistorical,
        "nodal"             : KratosMultiphysics.Expression.ContainerType.NodalNonHistorical,
        "element"           : KratosMultiphysics.Expression.ContainerType.ElementNonHistorical,
        "condition"         : KratosMultiphysics.Expression.ContainerType.ConditionNonHistorical
    }

    is_historical_container: "dict[str,bool]" = {
        "nodal_historical" : True,
        "nodal" : False,
        "element" : False,
        "condition" : False
    }
