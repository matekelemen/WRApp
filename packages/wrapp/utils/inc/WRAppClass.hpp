/// @author Máté Kelemen

#pragma once

// --- Core Includes ---
#include "includes/kratos_parameters.h"
#include "includes/smart_pointers.h"


namespace Kratos::WRApp {


/// @brief Dummy base class for registering and exporting exposed classes in @a WRApplication.
struct WRAppClass
{
    KRATOS_CLASS_POINTER_DEFINITION(WRAppClass);

    WRAppClass() noexcept = default;

    WRAppClass(WRAppClass&& rOther) noexcept = default;

    WRAppClass(const WRAppClass& rOther) noexcept = default;

    WRAppClass& operator=(WRAppClass&& rOther) noexcept = default;

    WRAppClass& operator=(const WRAppClass& rOther) noexcept = default;

    virtual Parameters GetDefaultParameters() const = 0;
}; // struct WRAppClass


} // namespace Kratos::WRApp
