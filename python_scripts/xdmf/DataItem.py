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



class LeafDataItem(DataItem):

    def __init__(self, data: Data) -> None:
        super().__init__()
        self.attrib.update(data.GetAttributes())
        self.attrib["ItemType"] = "Uniform"
        self.text = data.GetText()



class UniformDataItem(DataItem):

    def __init__(self, child: DataItem) -> None:
        super().__init__()
        self.append(child)
        self.attrib.update(child.attrib)
        self.attrib["ItemType"] = "Uniform"



class CoordinateDataItem(DataItem):

    def __init__(self,
                 index_set: DataItem,
                 reference_set: DataItem) -> None:
        super().__init__()
        self.attrib.update(reference_set.attrib)

        # Even though indices are supposed to be integers, Paraview
        # will crap out if that's explicitly mentioned.
        for attribute_name in ("DataType", "Precision"):
            if attribute_name in index_set.attrib:
                del index_set.attrib[attribute_name]

        # Paraview drops the ball if nested items have names
        for element in (index_set, reference_set):
            if "Name" in element.attrib:
                del element.attrib["Name"]

        self.append(index_set)
        self.append(reference_set)

        # Both of the following attributes are necessary for Paraview,
        # with this exact capitalization ...
        self.attrib["ItemType"] = "coordinates"
        self.attrib["Type"] = "Coordinate"

        # The coordinate format restricts the size of its reference
        # data item.
        index_shape = [int(d) for d in index_set.attrib["Dimensions"]]
        reference_shape = [int(d) for d in index_set.attrib["Dimensions"]]

        if not all(i <= r for i, r in zip(index_shape, reference_shape)):
            raise RuntimeError(f"incompatible shapes (index set: {index_shape}, reference set {reference_shape})")

        self.attrib["Dimensions"] = " ".join(str(d) for d in index_shape + reference_shape[len(index_shape):])
