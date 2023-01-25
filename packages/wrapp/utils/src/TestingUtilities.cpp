//    |  /           |
//    ' /   __| _` | __|  _ \   __|
//    . \  |   (   | |   (   |\__ `
//   _|\_\_|  \__,_|\__|\___/ ____/
//                   Multi-Physics
//
//  License:         BSD License
//                   license: HDF5Application/license.txt
//
//  Main author:     Máté Kelemen
//

#ifdef KRATOS_BUILD_TESTING

// --- WRApp Includes ---
#include "wrapp/utils/inc/TestingUtilities.hpp"

// --- Core Includes ---
#include "utilities/parallel_utilities.h"


namespace Kratos::Testing {


void TestingUtilities::TestJournal(const Model& rModel, Journal& rJournal)
{
    constexpr const std::size_t iteration_count = 1e2;
    IndexPartition<>(iteration_count).for_each([&rModel,&rJournal](std::size_t index){
        rJournal.Push(rModel);
    });
}


} // namespace Kratos::Testing


#endif // KRATOS_BUILD_TESTING
