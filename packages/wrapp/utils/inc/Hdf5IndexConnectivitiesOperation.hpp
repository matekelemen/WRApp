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


class KRATOS_API(WR_APPLICATION) Hdf5IndexConnectivitiesOperation final : public WRAppClass
{
public:
    KRATOS_CLASS_POINTER_DEFINITION(Hdf5IndexConnectivitiesOperation);

    Hdf5IndexConnectivitiesOperation();

    Hdf5IndexConnectivitiesOperation(Parameters Settings);

    Hdf5IndexConnectivitiesOperation(Ref<Model> rModel, Parameters Settings);

    Hdf5IndexConnectivitiesOperation(const Hdf5IndexConnectivitiesOperation& rRhs);

    Hdf5IndexConnectivitiesOperation& operator=(const Hdf5IndexConnectivitiesOperation& rRhs);

    ~Hdf5IndexConnectivitiesOperation() override;

    void Execute();

    Parameters GetDefaultParameters() const override;

private:
    struct Impl;
    std::unique_ptr<Impl> mpImpl;
}; // class Hdf5IndexConnectivitiesOperation


} // namespace Kratos::WRApp
