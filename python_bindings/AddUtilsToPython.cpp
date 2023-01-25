/// @author Máté Kelemen

// --- WRApp Includes ---
#include "wrapp/utils/inc/AddUtilsToPython.hpp"
#include "wrapp/utils/inc/PatternUtility.hpp"


namespace Kratos::Python {


namespace {
/// @brief Collect globbed paths to an array of strings.
std::vector<std::filesystem::path> Glob (const ModelPartPattern& rInstance) {
    std::vector<std::filesystem::path> output;
    rInstance.Glob(std::back_inserter(output));
    return output;
}
} // namespace


void AddUtilsToPython(pybind11::module& rModule)
{
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
        .def("Apply",
             static_cast<std::string(CheckpointPattern::*)(const CheckpointPattern::PlaceholderMap&)const>(&CheckpointPattern::Apply),
             "Substitute values from the input map into the stored pattern.")
        .def("Apply",
             static_cast<std::string(CheckpointPattern::*)(const ModelPart&,std::size_t)const>(&CheckpointPattern::Apply),
             "Substitute values from the provided model part and path ID into the stored pattern.")
        ;

    #ifdef KRATOS_BUILD_TESTING // <== defined through CMake if cpp test sources are built
    pybind11::class_<Testing::TestingUtilities, std::shared_ptr<Testing::TestingUtilities>>(rModule, "TestingUtilities")
        .def_static("TestJournal", &Testing::TestingUtilities::TestJournal)
        ;
    #endif
}


} // namespace Kratos::Python
