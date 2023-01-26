/// @author Máté Kelemen

#pragma once

// --- Core Includes ---
#include "includes/define.h"
#include "includes/variables.h"
#include "includes/kratos_application.h"


namespace Kratos {


/// Additional identifier for solution steps to help keeping track of them during checkpointing.
KRATOS_DEFINE_APPLICATION_VARIABLE(WR_APPLICATION, int, ANALYSIS_PATH);


} // namespace Kratos
