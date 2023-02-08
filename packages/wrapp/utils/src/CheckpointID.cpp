/// @author Máté Kelemen

// --- WRApp Includes ---
#include "wrapp/utils/inc/CheckpointID.hpp"


namespace Kratos::WRApp {


CheckpointID::CheckpointID() noexcept
    : CheckpointID(0, 0)
{
}


CheckpointID::CheckpointID(int step, int path) noexcept
    : mStep(step),
      mPath(path)
{
}


int CheckpointID::GetStep() const noexcept
{
    return this->mStep;
}


int CheckpointID::GetAnalysisPath() const noexcept
{
    return this->mPath;
}


std::ostream& operator<<(std::ostream& rStream, CheckpointID ID)
{
    rStream << "(step: " << ID.mStep << ", path: " << ID.mPath << ')';
    return rStream;
}


} // namespace Kratos::WRApp
