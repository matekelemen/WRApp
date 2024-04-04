""" @author Máté Kelemen"""

__all__ = [
    "DataType",
    "Int",
    "UInt",
    "Float"
]

# --- STD Imports ---
import abc



class DataType(abc.ABC):

    @abc.abstractmethod
    def GetAttributes(self) -> "list[tuple[str,str]]":
        return []



class Int(DataType):

    def __init__(self, precision: int) -> None:
        super().__init__()
        if not isinstance(precision, int):
            raise TypeError(f"expecting an integer, got {type(precision)}")
        self.__precision = precision


    def GetAttributes(self) -> "list[tuple[str,str]]":
        return [("NumberType", "Int"), ("Precision", str(self.__precision))]



class UInt(DataType):

    def __init__(self, precision: int) -> None:
        super().__init__()
        if not isinstance(precision, int):
            raise TypeError(f"expecting an integer, got {type(precision)}")
        self.__precision = precision


    def GetAttributes(self) -> "list[tuple[str,str]]":
        return [("NumberType", "UInt"), ("Precision", str(self.__precision))]



class Float(DataType):

    def __init__(self, precision: int) -> None:
        super().__init__()
        if not isinstance(precision, int):
            raise TypeError(f"expecting an integer, got {type(precision)}")
        self.__precision = precision


    def GetAttributes(self) -> "list[tuple[str,str]]":
        return [("NumberType", "Float"), ("Precision", str(self.__precision))]
