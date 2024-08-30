/// @author Máté Kelemen

// --- Core Includes ---
#include "testing/testing.h"

// --- STL Includes ---
#include <memory> // std::unique_ptr


namespace Kratos::Testing {

class WRAppTestSuite : public KratosCoreFastSuite
{
public:
    WRAppTestSuite();

    ~WRAppTestSuite();

private:
    struct Impl;
    std::unique_ptr<Impl> mpImpl;
}; // class WRAppTestSuite

} // namespace Kratos::Testing
