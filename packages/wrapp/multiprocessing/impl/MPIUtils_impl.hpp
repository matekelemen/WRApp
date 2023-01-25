/// @author Máté Kelemen

#pragma once

// --- Core Includes ---
#include "includes/data_communicator.h"

// --- WRApp Includes ---
#include "wrapp/multiprocessing/inc/MPIUtils.hpp"

// --- STL Includes ---
#include <vector>


namespace Kratos::WRApp {


template <class TInputIterator, class TOutputIterator>
void MPIUtils::AllGatherV(TInputIterator itBegin,
                          TInputIterator itEnd,
                          TOutputIterator itOutput,
                          DataCommunicator& rCommunicator)
{
    using Value = typename std::iterator_traits<TInputIterator>::value_type;

    const int this_rank = rCommunicator.Rank();
    const int number_of_ranks = rCommunicator.Size();

    const int send_to = (this_rank + 1) % number_of_ranks;
    const int receive_from = (number_of_ranks + this_rank - 1) % number_of_ranks;

    std::vector<Value> output_buffer(itBegin, itEnd);
    std::vector<Value> communication_buffer = output_buffer;

    for (int i_rank=0; i_rank<number_of_ranks-1; ++i_rank) {
        // Forward new data
        // - if this is the first iteration, the rank-local data is sent
        // - if this is not the first iteration, the last received data is sent
        communication_buffer = rCommunicator.SendRecv(communication_buffer, send_to, receive_from);
        output_buffer.reserve(output_buffer.size() + communication_buffer.size());

        // Copy received data to the output buffer
        std::copy(communication_buffer.begin(), communication_buffer.end(), std::back_inserter(output_buffer));
    }

    // Move items from the output buffer to the output range
    for (Value& r_item : output_buffer) {
        *itOutput++ = std::move(r_item);
    }
}


} // namespace Kratos::WRApp
