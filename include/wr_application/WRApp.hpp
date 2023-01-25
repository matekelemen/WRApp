#pragma once

// --- Core Includes ---
#include "includes/kratos_application.h"

// --- STL Includes ---
#include <ostream>


namespace Kratos {

///@name Kratos Classes
///@{

class KRATOS_API(WR_APPLICATION) WRApp : public KratosApplication {
public:
    ///@name Type Definitions
    ///@{

    KRATOS_CLASS_POINTER_DEFINITION(WRApp);

    ///@}
    ///@name Life Cycle
    ///@{

    /// Default constructor.
    WRApp();

    /// Destructor.
    ~WRApp() override {}

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
    ///@name Un accessible methods
    ///@{

    WRApp& operator=(const WRApp& rOther) = delete;

    WRApp(const WRApp& rOther) = delete;

    ///@}

}; // class WRApp

///@}


} // namespace Kratos
