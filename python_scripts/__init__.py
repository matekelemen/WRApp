from KratosMultiphysics import _ImportApplication
from WRApp import *

application = WRApp()
application_name = "WRApp"

_ImportApplication(application, application_name)
