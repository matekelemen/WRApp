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
class KRATOS_API(WR_APPLICATION) Hdf5LinSpaceOperation final : public WRAppClass
{
public:
    KRATOS_CLASS_POINTER_DEFINITION(Hdf5LinSpaceOperation);

    Hdf5LinSpaceOperation();

    Hdf5LinSpaceOperation(Parameters Settings);

    Hdf5LinSpaceOperation(Ref<Model> rModel, Parameters Settings);

    Hdf5LinSpaceOperation(const Hdf5LinSpaceOperation& rRhs);

    Hdf5LinSpaceOperation& operator=(const Hdf5LinSpaceOperation& rRhs);

    ~Hdf5LinSpaceOperation() override;

    void Execute();

    Parameters GetDefaultParameters() const override;

private:
    struct Impl;
    std::unique_ptr<Impl> mpImpl;
}; // class Hdf5LinSpaceOperation


} // namespace Kratos::WRApp
