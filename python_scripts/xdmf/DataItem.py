""" @author Máté Kelemen"""

__all__ = [
    "DataItem",
    "LeafDataItem",
    "UniformDataItem",
    "CoordinateDataItem",
    "MakeCoordinateSlice"
]

# --- WRApp Imports ---
from KratosMultiphysics.WRApplication.xdmf.Data import Data

# --- STD Imports ---
import abc
from xml.etree.ElementTree import Element
from typing import Collection, Optional
from operator import mul
from functools import reduce



class DataItem(abc.ABC, Element):

    def __init__(self) -> None:
        abc.ABC.__init__(self)
        Element.__init__(self, "DataItem", {})


    @abc.abstractmethod
    def GetShape(self) -> "list[int]":
        pass



class LeafDataItem(DataItem):

    def __init__(self, data: Data) -> None:
        super().__init__()
        self.attrib.update(data.GetAttributes())
        self.attrib["ItemType"] = "Uniform"
        self.text = data.GetText()
        self.__shape = data.GetShape()


    def GetShape(self) -> "list[int]":
        return self.__shape



class UniformDataItem(DataItem):

    def __init__(self, child: DataItem) -> None:
        super().__init__()
        self.append(child)
        self.attrib.update(child.attrib)
        self.attrib["ItemType"] = "Uniform"


    def GetShape(self) -> "list[int]":
        child: DataItem = self[0]
        return child.GetShape()



class CoordinateDataItem(DataItem):

    def __init__(self,
                 index_set: DataItem,
                 reference_set: DataItem,
                 rank: int = 1) -> None:
        super().__init__()
        self.attrib.update(reference_set.attrib)
        self.attrib["ItemType"] = "Coordinates"
        if "Format" in self.attrib:
            del self.attrib["Format"]

        self.append(index_set)
        self.append(reference_set)

        # The coordinate format restricts the size of its reference
        # data item.
        index_shape = index_set.GetShape()
        reference_shape = reference_set.GetShape()

        if len(index_shape) != len(reference_shape):
            raise RuntimeError(f"rank mismatch between index and reference sets (index set shape: {index_shape}, reference set shape: {reference_shape})")

        self.__shape: "list[int]" = index_shape[:1] + [1 for _ in range(rank - 1)]
        self.attrib["Dimensions"] = " ".join(str(v) for v in self.__shape)


    def GetShape(self) -> "list[int]":
        return self.__shape.copy()



class __FunctionDataItem(DataItem):
    """ @brief Internal type for dirty tricks."""

    def __init__(self,
                 function_definition: str,
                 shape: Collection[int],
                 attributes: "Collection[tuple[str,str]]") -> None:
        super().__init__()
        self.__shape = [v for v in shape]
        self.attrib.update(attributes)
        self.attrib["ItemType"] = "Function"
        self.attrib["Function"] = function_definition
        self.attrib["Dimensions"] = " ".join(str(v) for v in self.__shape)


    def GetShape(self) -> "list[int]":
        return self.__shape.copy()



def MakeCoordinateSlice(index_set: DataItem,
                        reference_set: DataItem,
                        component_indices: "list[int]") -> Optional[DataItem]:
    index_shape = index_set.GetShape()
    reference_shape = reference_set.GetShape()

    # The "Function" DataItem in XDMF has an annoying behavior change when its child DataItem
    # has only a single value: instead of referencing the array it directly copies its value
    # into the expression, which is then no longer a valid argument to JOIN.
    # Long story short: if the index set has only a single value it has to be handled separately.
    # In this case: refuse to generate a DataItem.
    if reduce(mul, index_shape, 1) == 1:
        return None

    if len(index_shape) == len(reference_shape):
        if len(component_indices):
            raise RuntimeError(f"index and reference sets have matching ranks, but the list of selected components () is not empty")
        return CoordinateDataItem(index_set, reference_set, rank = 2)
    elif len(reference_shape) - len(index_shape) == 1:
        output: DataItem
        if len(component_indices) == 1:
            component_set = __FunctionDataItem("JOIN($0, 0*$0)",
                                               index_shape + [2],
                                               reference_set.attrib.items())
            component_set.append(index_set)
            output = CoordinateDataItem(component_set, reference_set, rank = 2)
        else:
            operands: "list[DataItem]" = []
            operand_shape = index_shape + [2]

            for i_component in component_indices:
                component_set = __FunctionDataItem(
                    f"JOIN($0, {f'{i_component} + ' if i_component else ''}0*$0)",
                    operand_shape,
                    reference_set.attrib.items())
                component_set.append(index_set)
                operands.append(CoordinateDataItem(component_set, reference_set))

            output = __FunctionDataItem(f"JOIN({', '.join(f'${i}' for i in range(len(component_indices)))})",
                                        index_shape + [len(component_indices)],
                                        reference_set.attrib.items())
            for operand in operands:
                output.append(operand)

        return output
    else:
        raise RuntimeError(f"multidimensional slices are not supported")

