/// @author Máté Kelemen

#pragma once

// --- WRApp Includes ---
#include "wrapp/utils/inc/CheckpointID.hpp"


namespace Kratos::WRApp {


bool operator==(CheckpointID left, CheckpointID right) noexcept
{
    return left.mPath == right.mPath && left.mStep == right.mStep;
}


bool operator!=(CheckpointID left, CheckpointID right) noexcept
{
    return !(left == right);
}


bool operator<(CheckpointID left, CheckpointID right) noexcept
{
    return left.mStep < right.mStep || left.mPath < right.mPath;
}


} // namespace Kratos::WRApp
