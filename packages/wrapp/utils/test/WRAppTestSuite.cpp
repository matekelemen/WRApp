/// @author Máté Kelemen

// --- WRApp Includes ---
#include "wr_application/WRApplication.hpp"
#include "wrapp/utils/inc/WRAppTestSuite.hpp"


namespace Kratos::Testing {


struct WRAppTestSuite::Impl
{
    KratosApplication::Pointer mpApp;
}; // struct WRAppTestSuite::Impl


WRAppTestSuite::WRAppTestSuite()
    : KratosCoreFastSuite(),
      mpImpl(new Impl {KratosApplication::Pointer(new KratosWRApplication)})
{
    this->ImportApplicationIntoKernel(mpImpl->mpApp);
}


WRAppTestSuite::~WRAppTestSuite() = default;


} // namespace Kratos::Testing

