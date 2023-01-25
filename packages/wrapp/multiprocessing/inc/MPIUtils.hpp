/// @author Máté Kelemen

#pragma once

// --- Core Includes ---
#include "includes/data_communicator.h"


namespace Kratos::WRApp {


struct MPIUtils
{
    /**
     *  @brief Synchronize a union of all items on every rank.
     *  @warning This function is only meant to be used for trivially serializable
     *           value types.
     */
    template <class TInputIterator, class TOutputIterator>
    static void AllGatherV(TInputIterator itBegin,
                           TInputIterator itEnd,
                           TOutputIterator itOutput,
                           DataCommunicator& rCommunicator);
}; // struct MPIUtils


} // namespace Kratos::WRApp

#include "wrapp/multiprocessing/impl/MPIUtils_impl.hpp"
