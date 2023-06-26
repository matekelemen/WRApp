""" @author Máté Kelemen"""

__all__ = [
    "Debug"
]

# --- Core Imports ---
import KratosMultiphysics

# --- WRApp Imports ---
from .types import Typing


class Debug:

    @staticmethod
    def PlotExpression(expression: Typing.ContainerExpression,
                       show = True,
                       block = True) -> None:
        array = KratosMultiphysics.Vector(len(expression.GetContainer()) * expression.GetItemComponentCount())
        KratosMultiphysics.Expression.CArrayExpressionIO.Write(expression, array)
        from matplotlib import pyplot
        pyplot.plot(array)
        if show:
            pyplot.show(block = block)
