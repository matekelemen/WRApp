/// @author Máté Kelemen

// --- WRApplication Includes ---
#include "wr_application/WRApplication.hpp"
#include "wr_application/WRApplication_variables.hpp"


namespace Kratos {


KratosWRApplication::KratosWRApplication()
    : KratosApplication("WRApplication")
{
}


void KratosWRApplication::Register()
{
    KRATOS_INFO("") << "Initializing WRApplication..." << std::endl;

    // Register custom variables
    KRATOS_REGISTER_VARIABLE(ANALYSIS_PATH)
}


std::string KratosWRApplication::Info() const
{
    return "KratosWRApplication";
}


void KratosWRApplication::PrintInfo(std::ostream& rStream) const
{
    rStream << this->Info();
    this->PrintData(rStream);
}


void KratosWRApplication::PrintData(std::ostream& rStream) const
{
    KRATOS_WATCH("In WRApplication:");
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
