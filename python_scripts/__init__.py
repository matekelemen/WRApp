"""@author Máté Kelemen"""

# --- Core Imports ---
import KratosMultiphysics
from KratosWRApplication import *

# --- WRApp Imports ---
from .registry_utils import RegisterClass,              \
                            RecursivelyRegisterClass,   \
                            GetRegistryEntry,           \
                            GetRegisteredClass,         \
                            RegisteredClassFactory,     \
                            IsRegisteredPath,           \
                            ImportAndRegister

# --- STD Imports ---
import abc


# Rename WRAppClass because it'll have to be replaced,
# since abc.ABC and classes wrapped by pybind aren't
# compatible.
__WRAppClass = globals()["WRAppClass"]
del globals()["WRAppClass"]

application = KratosWRApplication()
application_name = "WRApplication"

# Register every C++ class that inherits from WRAppClass
for subclass in __WRAppClass.__subclasses__():
    RecursivelyRegisterClass(subclass, application_name)

# Invoke the core import mechanism
KratosMultiphysics._ImportApplication(application, application_name)


class WRAppMeta(type(abc.ABC), type(__WRAppClass)):
    """ @brief Metaclass replacing that of the C++ WRAppClass to provide derived classes access to abc.ABCMeta.
        @classname WRAppMeta
    """
    pass


class WRAppClass(__WRAppClass, metaclass = WRAppMeta):
    """ @brief @ref WRApp::WRAppClass with a replaced metaclass for compatibility with abc.
        @classname WRAppClass
    """

    def __init__(self):
        super().__init__()


    @abc.abstractmethod
    def GetDefaultParameters(self) -> KratosMultiphysics.Parameters:
        pass


# --- WRApp Imports ---
from .utilities import *
from .TestCase import *
from .MPIUtils import *
from .checkpoint import *
from .coupling import *
from .async_analysis import *
from .Launcher import *
from .cli import *


# Register every python class that inherits from WRAppClass
for subclass in WRAppClass.__subclasses__():
    RecursivelyRegisterClass(subclass, application_name)
