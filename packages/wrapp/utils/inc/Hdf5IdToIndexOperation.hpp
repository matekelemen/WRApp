/// @author Máté Kelemen

#pragma once

// --- WRApp Includes ---
#include "wrapp/utils/inc/WRAppClass.hpp" // WRAppClass
#include "wrapp/utils/inc/common.hpp" // Ref

// --- Core Includes ---
#include "includes/smart_pointers.h" // KRATOS_CLASS_POINTER_DEFINITION
#include "containers/model.h" // Model

// --- STL Includes ---
#include <memory> // unique_ptr


namespace Kratos::WRApp {


/// @ingroup WRApplication
class KRATOS_API(WR_APPLICATION) Hdf5IdToIndexOperation final : public WRAppClass
{
public:
    KRATOS_CLASS_POINTER_DEFINITION(Hdf5IdToIndexOperation);

    Hdf5IdToIndexOperation();

    Hdf5IdToIndexOperation(Parameters Settings);

    Hdf5IdToIndexOperation(Ref<Model>, Parameters Settings);

    Hdf5IdToIndexOperation(const Hdf5IdToIndexOperation& rRhs);

    Hdf5IdToIndexOperation& operator=(const Hdf5IdToIndexOperation& rRhs);

    ~Hdf5IdToIndexOperation() override;

    void Execute();

    Parameters GetDefaultParameters() const override;

private:
    struct Impl;
    std::unique_ptr<Impl> mpImpl;
}; // class MapIdToIndexOperation


} // namespace Kratos::WRApp
