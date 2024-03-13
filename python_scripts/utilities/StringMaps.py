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

    containers: "dict[str,KratosMultiphysics.Globals.DataLocation]" = {
        "nodal_historical"  : KratosMultiphysics.Globals.DataLocation.NodeHistorical,
        "nodal"             : KratosMultiphysics.Globals.DataLocation.NodeNonHistorical,
        "element"           : KratosMultiphysics.Globals.DataLocation.Element,
        "condition"         : KratosMultiphysics.Globals.DataLocation.Condition
    }

    is_historical_container: "dict[str,bool]" = {
        "nodal_historical" : True,
        "nodal" : False,
        "element" : False,
        "condition" : False
    }
