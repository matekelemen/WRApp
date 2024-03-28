""" @author Máté Kelemen"""

__all__ = [
    "Domain"
]

# --- WRApp Imports ---
from KratosMultiphysics.WRApplication.xdmf.Grid import Grid

# --- STD Imports ---
from xml.etree.ElementTree import Element



class Domain(Element):

    def __init__(self) -> None:
        super().__init__("Domain")


    def append(self, grid: Grid) -> None:
        if not isinstance(grid, Grid):
            raise TypeError(f"expecting a Grid, but got {type(grid)}")
        return super().append(grid)
