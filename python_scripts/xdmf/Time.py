""" @author Máté Kelemen"""

__all__ = [
    "Time",
    "TimePoint",
    "TimeGrid",
    "TimeList"
]

# --- WRApp Imports ---
from KratosMultiphysics.WRApplication.xdmf.DataType import Float
from KratosMultiphysics.WRApplication.xdmf.Data import XmlData
from KratosMultiphysics.WRApplication.xdmf.DataItem import LeafDataItem

# --- STD Imports ---
from xml.etree.ElementTree import Element
from typing import Union, Collection



class Time(Element):

    def __init__(self) -> None:
        super().__init__("Time")



class TimePoint(Time):

    def __init__(self, value: Union[int,float]) -> None:
        super().__init__()
        self.attrib["TimeType"] = "Single"
        self.attrib["Value"] = str(value)



class TimeGrid(Time):

    def __init__(self, linspace: "tuple[float,float,float]") -> None:
        super().__init__()
        self.attrib["TimeType"] = "HyperSlab"
        self.append(LeafDataItem(XmlData(
            Float(8),
            [3],
            linspace
        )))



class TimeList(Time):

    def __init__(self, values: Collection[float]) -> None:
        super().__init__()
        self.attrib["TimeType"] = "List"
        self.append(LeafDataItem(XmlData(
            Float(8),
            [len(values)],
            values
        )))
