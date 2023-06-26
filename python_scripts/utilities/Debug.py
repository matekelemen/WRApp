""" @author Máté Kelemen"""

__all__ = [
    "Debug"
]

# --- External Imports ---
from matplotlib import pyplot

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
from .types import Typing

# --- STD Imports ---
import pathlib


class Debug:

    @staticmethod
    def PlotExpression(expression: Typing.ContainerExpression,
                       show = True,
                       block = True,
                       output_file_name: pathlib.Path = None) -> None:
        array = KratosMultiphysics.Vector(len(expression.GetContainer()) * expression.GetItemComponentCount())
        KratosMultiphysics.Expression.CArrayExpressionIO.Write(expression, array)

        figure, axes = pyplot.subplots()
        axes.plot(array)

        if output_file_name:
            figure.savefig(output_file_name)

        if show:
            pyplot.show(block = block)


