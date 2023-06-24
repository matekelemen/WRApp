/// @author Máté Kelemen

#pragma once

// --- Core Includes ---
#include "includes/kratos_parameters.h"
#include "includes/smart_pointers.h"
#include "includes/kratos_export_api.h"


namespace Kratos::WRApp {


/// @addtogroup WRApplication
/// @{


/// @brief Dummy base class for registering and exporting exposed classes in @a WRApplication.
struct KRATOS_API(WR_APPLICATION) WRAppClass
{
    KRATOS_CLASS_POINTER_DEFINITION(WRAppClass);

    virtual ~WRAppClass() noexcept = default;

    WRAppClass() noexcept = default;

    WRAppClass(WRAppClass&& rOther) noexcept = default;

    WRAppClass(const WRAppClass& rOther) noexcept = default;

    virtual ~WRAppClass() noexcept = default;

    WRAppClass& operator=(WRAppClass&& rOther) noexcept = default;

    WRAppClass& operator=(const WRAppClass& rOther) noexcept = default;

    virtual Parameters GetDefaultParameters() const = 0;
}; // struct WRAppClass


/// @}


} // namespace Kratos::WRApp
