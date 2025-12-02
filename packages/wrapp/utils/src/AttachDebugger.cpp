/// @author Máté Kelemen

// --- WRApp Includes ---
#include "wrapp/utils/inc/AttachDebugger.hpp"

// --- Core Includes ---
#include "includes/exception.h"

// --- STL Includes ---
#include <sstream>
#include <iostream>
#include <chrono>
#include <thread>
#if defined(__linux__) || defined(__unix__)
#include <unistd.h>
#endif


namespace Kratos::WRApp {


void AttachDebugger()
{
    int pid = 0;
    #if defined(__linux__) || defined(__unix__)
        pid = ::getpid();
    #else
        KRATOS_ERROR << "Attaching a debugger on the current platform is not supported yet.";
    #endif

    std::stringstream command;
    #if defined(__linux__)
        command << "konsole --hold -e \"gdb -p " << pid << "\" 2>&1 &";
    #elif defined(__unix__)
        KRATOS_ERROR << "ToDo on UNIX systems.";
    #endif

    std::flush(std::cout);
    std::flush(std::cerr);
    std::cout << command.str().c_str() << std::endl;
    std::system(command.str().c_str());

    std::this_thread::sleep_for(std::chrono::seconds(1));
}


} // namespace Kratos::WRApp
