/// @author Máté Kelemen

#pragma once


namespace Kratos::WRApp {


class CheckpointID
{
public:
    /// @brief Default constructor initialized to null.
    CheckpointID() noexcept;

    /// @arg step. @ref STEP
    /// @arg path: @ref ANALYSIS_PATH
    CheckpointID(int step, int path) noexcept;

    CheckpointID(CheckpointID&&) noexcept = default;

    CheckpointID(const CheckpointID&) noexcept = default;

    /// @return @ref STEP.
    int GetStep() const noexcept;

    /// @return @ref ANALYSIS_PATH.
    int GetAnalysisPath() const noexcept;

    /// @brief True if both @ref ANALYSIS_PATH and @ref STEP are identical across operands.
    friend bool operator==(CheckpointID left, CheckpointID right) noexcept;

    /// @brief True if @ref ANALYSIS_PATH or @ref STEP are not equal.
    friend bool operator!=(CheckpointID left, CheckpointID right) noexcept;

    /// @brief Lexicographical comparison on [@ref STEP, @ref ANALYSIS_PATH].
    friend bool operator<(CheckpointID left, CheckpointID right) noexcept;

private:
    /// @brief @ref STEP
    int mStep;

    /// @brief @ref ANALYSIS_PATH
    int mPath;
}; // class CheckpointID


} // namespace Kratos::WRApp

#include "wrapp/utils/impl/CheckpointID_impl.hpp"
