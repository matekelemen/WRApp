"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics
from KratosWRApplication import *

# --- STD Imports ---
import typing
import abc

# Rename WRAppClass because it'll have to be replaced
__WRAppClass = globals()["WRAppClass"]
del globals()["WRAppClass"]

application = KratosWRApplication()
application_name = "WRApplication"

def __RegisterClassRecursive(cls: type, parent_path: str):
    """@brief Recursively add all exposed classes to the Registry.
       @details Exposed classes are the ones directly or indirectly
                deriving from WRAppClass."""
    KratosMultiphysics.Registry.AddItem(f"{parent_path}.{cls.__name__}", {"type" : cls})
    new_parent_path = ("." if parent_path else "").join((parent_path, cls.__name__))
    for subclass in cls.__subclasses__():
        __RegisterClassRecursive(subclass, new_parent_path)

# Register every C++ class that inherits from WRAppClass
for subclass in __WRAppClass.__subclasses__():
    __RegisterClassRecursive(subclass, application_name)

# Invoke the core import mechanism
KratosMultiphysics._ImportApplication(application, application_name)


# Define a metaclass to replace that of the C++ WRAppClass
# to make a python class able to derive from both abc.ABCMeta
# and a C++ class.
class WRAppMeta(type(abc.ABC), type(__WRAppClass)): pass


class WRAppClass(__WRAppClass, metaclass = WRAppMeta):
    """@brief @ref WRApp::WRAppClass with a replaced metaclass for compatibility with abc."""

    def __init__(self):
        super().__init__()


    @abc.abstractmethod
    def GetDefaultParameters(self) -> KratosMultiphysics.Parameters:
        pass


# --- WRApp Imports ---
from .checkpoint import *
from .TestCase import *


# Register every python class that inherits from WRAppClass
for subclass in WRAppClass.__subclasses__():
    __RegisterClassRecursive(subclass, application_name)
