/// @author Máté Kelemen

#pragma once

// --- External Includes ---
#include <pybind11/pybind11.h>

// --- Core Includes ---
#include "includes/define_python.h"


namespace Kratos::Python {


void AddIOToPython(pybind11::module& rModule);


} // namespace Kratos::Python
