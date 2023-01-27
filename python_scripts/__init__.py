"""@author Máté Kelemen"""

# --- Core Imports ---
from KratosMultiphysics import _ImportApplication
from KratosWRApplication import *

application = KratosWRApplication()
application_name = "WRApplication"

_ImportApplication(application, application_name)

# --- WRApp Imports ---
from .WRAppClass import WRAppClass # <== base class of exposed classes
from .checkpoint import *
from .TestCase import *

# --- STD Imports ---
import typing


def RegisterWRAppClass(cls: typing.Type[WRAppClass], parent_path: str):
    """@brief Recursively add all exposed classes to the Registry.
       @details Exposed classes are the ones directly or indirectly
                deriving from WRAppClass."""
    KratosMultiphysics.Registry.AddItem(cls.__name__, cls)
    new_parent_path = ("." if parent_path else "").join((parent_path, cls.__name__))
    for subclass in cls.__subclasses__():
        RegisterWRAppClass(subclass, new_parent_path)


for subclass in WRAppClass.__subclasses__():
    RegisterWRAppClass(subclass, "")
