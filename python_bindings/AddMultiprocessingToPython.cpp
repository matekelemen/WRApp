/// @author Máté Kelemen

// --- WRApp Includes ---
#include "wrapp/multiprocessing/inc/AddMultiprocessingToPython.hpp"
#include "wrapp/multiprocessing/inc/MPIUtils.hpp"


namespace Kratos::Python {


void AddMultiprocessingToPython(pybind11::module& rModule)
{
    rModule.def("MPIAllGatherVStrings",
                [](const std::vector<std::string>& rStrings, DataCommunicator& rCommunicator) -> std::vector<std::string> {
                    std::vector<std::string> output;
                    WRApp::MPIUtils::AllGatherV(rStrings.begin(),
                                                rStrings.end(),
                                                std::back_inserter(output),
                                                rCommunicator);
                    return output;
                },
                "A terrible reimplementation of MPI_Allgatherv for std::string")
    ;
}


} // namespace Kratos::Python
