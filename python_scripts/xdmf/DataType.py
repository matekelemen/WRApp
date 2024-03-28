""" @author Máté Kelemen"""

__all__ = [
    "DataType",
    "Int",
    "Double"
]

# --- STD Imports ---
import abc



class DataType(abc.ABC):

    @abc.abstractmethod
    def GetAttributes(self) -> "list[tuple[str,str]]":
        return []



class Int(DataType):

    def GetAttributes(self) -> "list[tuple[str,str]]":
        return [("DataType", "Int")]



class Double(DataType):

    def GetAttributes(self) -> "list[tuple[str,str]]":
        return [("DataType", "Float"), ("Precision", "8")]
