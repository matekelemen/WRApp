/// @author Máté Kelemen

#ifdef KRATOS_PYTHON

// --- External Includes ---
#include <pybind11/pybind11.h>

// --- Core Includes ---
#include "includes/define_python.h"

// --- WRApplication Includes ---
#include "wr_application/WRApplication.hpp"
#include "wr_application/WRApplication_variables.hpp"
#include "wrapp/io/inc/AddIOToPython.hpp"
#include "wrapp/utils/inc/AddUtilsToPython.hpp"
#include "wrapp/multiprocessing/inc/AddMultiprocessingToPython.hpp"
#include "wrapp/numeric/inc/AddNumericToPython.hpp"
#include "wrapp/pipes/inc/AddPipesToPython.hpp"


namespace Kratos::Python{


PYBIND11_MODULE(KratosWRApplication, module)
{
    pybind11::class_<KratosWRApplication,
                     KratosWRApplication::Pointer,
                     KratosApplication>(module, "KratosWRApplication")
        .def(pybind11::init<>())
        ;

    AddUtilsToPython(module);
    AddIOToPython(module);
    AddMultiprocessingToPython(module);
    AddNumericToPython(module);
    AddPipesToPython(module);

    // Register custom variables
    KRATOS_REGISTER_IN_PYTHON_VARIABLE(module, ANALYSIS_PATH)

} // PYBIND11_MODULE


} // namespace Kratos::Python

#endif
