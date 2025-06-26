""" @author Máté Kelemen"""

__all__ = [
    "Data",
    "XmlData",
    "HDF5Data"
]

# --- External Imports ---
import numpy
try:
    import h5py
except ModuleNotFoundError:
    class h5py:
        class Group: pass
        class Dataset: pass

# --- WRApp Imports ---
from KratosMultiphysics.WRApplication.xdmf.DataType import DataType, Int, UInt, Float

# --- STD Imports ---
import abc
import pathlib
from typing import Collection, Union, Optional



class Data(abc.ABC):

    def __init__(self, data_type: DataType, shape: "Collection[int]") -> None:
        self.__data_type = data_type
        self.__shape = [v for v in shape]


    def GetAttributes(self) -> "list[tuple[str,str]]":
        output = self.__data_type.GetAttributes()
        output.append(("Dimensions", " ".join(str(component) for component in self.__shape)))
        return output


    def GetShape(self) -> "list[int]":
        return self.__shape.copy()


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
        return super().GetAttributes() + [("Format", "HDF")]


    def GetText(self) -> str:
        return f"{self.__file_path}:{self.__prefix}"


    @classmethod
    def FromDataset(cls, dataset: h5py.Dataset) -> "HDF5Data":
        file_path = pathlib.Path(dataset.file.filename)
        prefix = str(dataset.name)
        data_type: Optional[DataType] = {
            numpy.int8  : int(1),
            numpy.int32 : Int(4),
            numpy.int64 : Int(8),
            numpy.uint32 : UInt(4),
            numpy.uint64 : UInt(8),
            numpy.float32 : Float(4),
            numpy.float64 : Float(8)
        }.get(dataset.dtype, None)
        if dataset.dtype == numpy.int8: data_type = Int(1)
        elif dataset.dtype == numpy.int32: data_type = Int(4)
        elif dataset.dtype == numpy.int64: data_type = Int(8)
        elif dataset.dtype == numpy.uint32: data_type = UInt(4)
        elif dataset.dtype == numpy.uint64: data_type = UInt(8)
        elif dataset.dtype == numpy.float32: data_type = Float(4)
        elif dataset.dtype == numpy.float64: data_type = Float(8)
        else: raise TypeError(f"{file_path}:{prefix} unsupported data type {dataset.dtype}")
        return HDF5Data(data_type,
                        dataset.shape,
                        file_path,
                        prefix)
