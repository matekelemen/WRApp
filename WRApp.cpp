/// @author Máté Kelemen

// --- WRApp Includes ---
#include "wr_application/WRApp.hpp"
#include "wr_application/WRApp_variables.hpp"


namespace Kratos
{


WRApp::WRApp()
    : KratosApplication("WRApp")
{
}


void WRApp::Register()
{
    KRATOS_INFO("") << "Initializing WRApp..." << std::endl;

    // Register custom variables
    KRATOS_REGISTER_VARIABLE(ANALYSIS_PATH)
}


std::string WRApp::Info() const
{
    return "WRApp";
}


void WRApp::PrintInfo(std::ostream& rStream) const
{
    rStream << this->Info();
    this->PrintData(rStream);
}


void WRApp::PrintData(std::ostream& rStream) const
{
    KRATOS_WATCH("In WRApp:");
    KRATOS_WATCH(KratosComponents<VariableData>::GetComponents().size());
    rStream << "Variables:" << std::endl;
    KratosComponents<VariableData>().PrintData(rStream);
    rStream << std::endl;
    rStream << "Elements:" << std::endl;
    KratosComponents<Element>().PrintData(rStream);
    rStream << std::endl;
    rStream << "Conditions:" << std::endl;
    KratosComponents<Condition>().PrintData(rStream);
}


} // namespace Kratos