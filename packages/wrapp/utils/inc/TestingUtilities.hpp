/// @author Máté Kelemen

#pragma once

#ifdef KRATOS_BUILD_TESTING

/**
 *  This header contains tests that need to test the interaction
 *  of python objects within C++. This usually means making sure
 *  that python's dreaded global interpreter lock is avoided by
 *  non-python threads.
 */

// --- WRApp Includes ---
#include "wrapp/io/inc/Journal.hpp"


namespace Kratos::Testing {


struct KRATOS_API(WR_APPLICATION) TestingUtilities
{
    /**
     *  Construct a @ref Model and a @ref Journal in python, assign a python function
     *  object as an extractor to the journal, and attempt to call use the journal in
     *  a parallel environment.
     */
    static void TestJournal(const Model& rModel, Journal& rJournal);
};


} // namespace Kratos::Testing


#endif // KRATOS_BUILD_TESTING
