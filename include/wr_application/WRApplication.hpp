#pragma once

// --- Core Includes ---
#include "includes/kratos_application.h"

// --- STL Includes ---
#include <ostream>


namespace Kratos {

///@name Kratos Classes
///@{

class KRATOS_API(WR_APPLICATION) KratosWRApplication : public KratosApplication {
public:
    ///@name Type Definitions
    ///@{

    KRATOS_CLASS_POINTER_DEFINITION(KratosWRApplication);

    ///@}
    ///@name Life Cycle
    ///@{

    KratosWRApplication();

    ~KratosWRApplication() override {}

    ///@}
    ///@name Operations
    ///@{

    void Register() override;

    ///@}
    ///@name Input and output
    ///@{

    std::string Info() const override;

    void PrintInfo(std::ostream& rOStream) const override;

    void PrintData(std::ostream& rOStream) const override;

    ///@}
private:
    KratosWRApplication& operator=(const KratosWRApplication& rOther) = delete;

    KratosWRApplication(const KratosWRApplication& rOther) = delete;

}; // class KratosWRApplication

///@}


} // namespace Kratos
