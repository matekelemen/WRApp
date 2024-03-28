""" @author Máté Kelemen"""

__all__ = [
    "Data",
    "XmlData",
    "HDF5Data"
]

# --- WRApp Imports ---
from KratosMultiphysics.WRApplication.xdmf.DataType import DataType

# --- STD Imports ---
import abc
import pathlib
from typing import Collection, Union



class Data(abc.ABC):

    def __init__(self, data_type: DataType, shape: "Collection[int]") -> None:
        self.__data_type = data_type
        self.__shape = shape


    def GetAttributes(self) -> "list[tuple[str,str]]":
        output = self.__data_type.GetAttributes()
        output.append(("Dimensions", " ".join(str(component) for component in self.GetShape())))
        return output


    def GetShape(self) -> "list[int]":
        return [value for value in self.__shape]


    @abc.abstractmethod
    def GetText(self) -> str:
        return ""



class XmlData(Data):

    def __init__(self,
                 data_type: DataType,
                 shape: Collection[int],
                 values: Collection[Union[int,float]]) -> None:
        super().__init__(data_type, shape)
        self.__values = values


    def GetAttributes(self) -> "list[tuple[str,str]]":
        return super().GetAttributes() + [("Format", "XML")]


    def GetText(self) -> str:
        return " ".join(str(value) for value in self.__values)



class HDF5Data(Data):

    def __init__(self,
                 data_type: DataType,
                 shape: Collection[int],
                 file_path: pathlib.Path,
                 prefix: str) -> None:
        super().__init__(data_type, shape)
        self.__file_path = file_path
        self.__prefix = prefix


    def GetAttributes(self) -> "list[tuple[str,str]]":
        return super().GetAttributes() + [("Format", "HDF5")]


    def GetText(self) -> str:
        return f"{self.__file_path}:{self.__prefix}"
