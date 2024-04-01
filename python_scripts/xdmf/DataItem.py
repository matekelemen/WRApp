""" @author Máté Kelemen"""

__all__ = [
    "DataItem",
    "LeafDataItem",
    "UniformDataItem",
    "CoordinateDataItem"
]

# --- WRApp Imports ---
from KratosMultiphysics.WRApplication.xdmf.Data import Data

# --- STD Imports ---
import abc
from xml.etree.ElementTree import Element



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
                 reference_set: DataItem) -> None:
        super().__init__()
        self.attrib.update(reference_set.attrib)
        if "Format" in self.attrib:
            del self.attrib["Format"]

        # Paraview drops the ball if nested items have names
        #for element in (index_set, reference_set):
        #    for key in ("Name", "DataType", "Precision"):
        #        if key in element.attrib:
        #            del element.attrib[key]

        self.append(index_set)
        self.append(reference_set)

        # Both of the following attributes are necessary for Paraview,
        # with this exact capitalization ...
        self.attrib["ItemType"] = "coordinates"
        self.attrib["Type"] = "Coordinate"

        # The coordinate format restricts the size of its reference
        # data item.
        index_shape = index_set.GetShape()
        reference_shape = reference_set.GetShape()

        if not all(i <= r for i, r in zip(index_shape, reference_shape)):
            raise RuntimeError(f"incompatible shapes (index set: {index_shape}, reference set {reference_shape})")

        self.__shape: "list[int]" = index_shape + reference_shape[len(index_shape):]

        # Remove 1s from the shape (otherwise paraview craps out sometimes)
        shape = self.__shape.copy()
        if shape:
            shape = [v for v in shape if v != 1]
            if not shape:
                shape = [1]
        self.attrib["Dimensions"] = " ".join(str(d) for d in shape)


    def GetShape(self) -> "list[int]":
        return self.__shape.copy()
