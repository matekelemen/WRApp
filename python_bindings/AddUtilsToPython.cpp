/// @author Máté Kelemen

// --- External Includes ---
#include <pybind11/operators.h>

// --- Core Includes ---
#include "includes/kratos_components.h"

// --- WRApplication Includes ---
#include "wrapp/utils/inc/AddUtilsToPython.hpp"
#include "wrapp/utils/inc/PatternUtility.hpp"
#include "wrapp/utils/inc/TestingUtilities.hpp"
#include "wrapp/utils/inc/MapKeyRange.hpp"
#include "wrapp/utils/inc/CheckpointID.hpp"

// --- STL Includes ---
#include <vector>
#include <filesystem>
#include <sstream>


namespace Kratos::Python {


namespace {


/// @brief Collect globbed paths to an array of strings.
std::vector<std::filesystem::path> Glob (const ModelPartPattern& rInstance) {
    std::vector<std::filesystem::path> output;
    rInstance.Glob(std::back_inserter(output));
    return output;
}


/// @brief Get a list of registered names from @ref KratosComponents.
template <class TVariable>
pybind11::list GetComponentNames()
{
    pybind11::list names;
    for (const auto& r_name : WRApp::MakeConstMapKeyRange(KratosComponents<TVariable>::GetComponents())) {
        names.append(r_name);
    }
    return names;
}


} // namespace


void AddUtilsToPython(pybind11::module& rModule)
{
    rModule.def("GetGlobalFlagNames",
                GetComponentNames<Flags>,
                "Get a list of all registered global flag names.");

    pybind11::class_<PlaceholderPattern, PlaceholderPattern::Pointer>(rModule, "PlaceholderPattern")
        .def(pybind11::init<const std::string&,const PlaceholderPattern::PlaceholderMap&>())
        .def("IsAMatch",
             &PlaceholderPattern::IsAMatch,
             "Check whether a string satisfies the pattern")
        .def("Match",
             &PlaceholderPattern::Match,
             "Find all placeholders' values in the input string.")
        .def("Apply",
             &PlaceholderPattern::Apply,
             "Substitute values from the input map into the stored pattern.")
        .def("GetRegexString",
             &PlaceholderPattern::GetRegexString,
             "Get the string representation of the regex.")
        .def("IsConst",
             &PlaceholderPattern::IsConst,
             "Return true if the input pattern contains no placeholders.")
        ;

    pybind11::class_<ModelPartPattern, ModelPartPattern::Pointer, PlaceholderPattern>(rModule, "ModelPartPattern")
        .def(pybind11::init<const std::string&>())
        .def("Glob",
             &Glob,
             "Collect all file/directory paths that match the pattern.")
        .def("Apply",
             static_cast<std::string(ModelPartPattern::*)(const ModelPartPattern::PlaceholderMap&)const>(&ModelPartPattern::Apply),
             "Substitute values from the input map into the stored pattern.")
        .def("Apply",
             static_cast<std::string(ModelPartPattern::*)(const ModelPart&)const>(&ModelPartPattern::Apply),
             "Substitute values from the model part into the stored pattern.")
        ;

    pybind11::class_<CheckpointPattern, CheckpointPattern::Pointer, ModelPartPattern>(rModule, "CheckpointPattern")
        .def(pybind11::init<const std::string&>())
        ;

    pybind11::class_<WRApp::CheckpointID>(rModule, "CheckpointID")
        .def(pybind11::init<>())
        .def(pybind11::init<int,int>())
        .def("GetStep", &WRApp::CheckpointID::GetStep)
        .def("GetAnalysisPath", &WRApp::CheckpointID::GetAnalysisPath)
        .def(pybind11::self == pybind11::self)
        .def(pybind11::self != pybind11::self)
        .def(pybind11::self < pybind11::self)
        .def("__str__", [](const WRApp::CheckpointID& rThis) {
                std::stringstream stream;
                stream << rThis;
                return stream.str();
            })
        ;

    #ifdef KRATOS_BUILD_TESTING // <== defined through CMake if cpp test sources are built
    pybind11::class_<Testing::TestingUtilities, std::shared_ptr<Testing::TestingUtilities>>(rModule, "TestingUtilities")
        .def_static("TestJournal", &Testing::TestingUtilities::TestJournal)
        ;
    #endif
}


} // namespace Kratos::Python
