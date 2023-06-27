""" @author Máté Kelemen"""

__all__ = [
    "Typing"
]

# --- Core Imports ---
import KratosMultiphysics

# --- STD Imports ---
import typing


class Typing:

    Variable = typing.Union[
        KratosMultiphysics.StringVariable,
        KratosMultiphysics.BoolVariable,
        KratosMultiphysics.IntegerVariable,
        KratosMultiphysics.IntegerVectorVariable,
        KratosMultiphysics.DoubleVariable,
        KratosMultiphysics.VectorVariable,
        KratosMultiphysics.Array1DVariable3,
        KratosMultiphysics.Array1DVariable4,
        KratosMultiphysics.Array1DVariable6,
        KratosMultiphysics.Array1DVariable9,
        KratosMultiphysics.MatrixVariable,
        KratosMultiphysics.ConstitutuveLawVariable,
        KratosMultiphysics.ConvectionDiffusionSettingsVariable,
        KratosMultiphysics.RadiationSettingsVariable,
        KratosMultiphysics.DoubleQuaternionVariable
    ]

    ContainerExpression = typing.Union[
        KratosMultiphysics.Expression.NodalExpression,
        KratosMultiphysics.Expression.ElementExpression,
        KratosMultiphysics.Expression.ConditionExpression
    ]
