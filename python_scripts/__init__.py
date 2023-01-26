from KratosMultiphysics import _ImportApplication
from KratosWRApplication import *

application = KratosWRApplication()
application_name = "WRApplication"

_ImportApplication(application, application_name)

from .checkpoint import *
