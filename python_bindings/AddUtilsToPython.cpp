/// @author Máté Kelemen

// --- External Includes ---
#include <pybind11/pybind11.h>
#include <pybind11/operators.h>

// --- Core Includes ---
#include "includes/kratos_components.h"
#include "utilities/parallel_utilities.h"

// --- WRApplication Includes ---
#include "wrapp/utils/inc/AddUtilsToPython.hpp"
#include "wrapp/utils/inc/WRAppClass.hpp"
#include "wrapp/utils/inc/ModelPredicate.hpp"
#include "wrapp/utils/inc/PatternUtility.hpp"
#include "wrapp/utils/inc/TestingUtilities.hpp"
#include "wrapp/utils/inc/MapKeyRange.hpp"
#include "wrapp/utils/inc/CheckpointID.hpp"
#include "wrapp/utils/inc/DataValueContainerKeyIterator.hpp"
#include "wrapp/utils/inc/DynamicEntityProxy.hpp"

// --- STL Includes ---
#include <type_traits>
#include <vector>
#include <filesystem>
#include <sstream>


namespace Kratos::Python {


namespace {


/// @brief Trampoline class for binding pure virtual @ref WRAppClass.
struct WRAppClassTrampoline : WRApp::WRAppClass
{
    Parameters GetDefaultParameters() const override
    {
        using WRAppClass = WRApp::WRAppClass;
        PYBIND11_OVERRIDE_PURE(
            Parameters,
            WRAppClass,
            GetDefaultParameters
        );
    }
}; // struct WRAppClassTrampoline


/// @brief Wrapper class for binding a pure virtual class.
class KRATOS_API(WR_APPLICATION) ModelPredicateTrampoline : public WRApp::ModelPredicate
{
public:
    bool operator()(const Model& rModel) const override
    {
        using ReturnType = bool;
        using BaseType = WRApp::ModelPredicate;
        PYBIND11_OVERRIDE_PURE(
            ReturnType,
            BaseType,
            operator(),
            rModel
        );
    }
}; // class ModelPredicateTrampoline


/// @brief Collect globbed paths to an array of strings.
std::vector<std::filesystem::path> Glob (const PlaceholderPattern& rInstance) {
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


struct FlagArray {std::vector<Flags> data;};


template <class TContainer, std::enable_if_t<std::is_base_of_v<Flags,typename TContainer::value_type>,bool> = true>
FlagArray GetFlags(const TContainer& rContainer, Flags mask)
{
    FlagArray output {std::vector<Flags>(rContainer.size())};
    IndexPartition<>(rContainer.size()).for_each([&output, &rContainer, mask](std::size_t i_item) {
        output.data[i_item] = *(rContainer.begin() + i_item) & mask;
    });
    return output;
}


template <class TContainer, std::enable_if_t<std::is_base_of_v<Flags,typename TContainer::value_type>,bool> = true>
void SetFlags(TContainer& rContainer, const FlagArray& rFlags, Flags mask)
{
    KRATOS_ERROR_IF_NOT(rContainer.size() == rFlags.data.size())
        << "Size mismatch (target container: " << rContainer.size()
        << ", source container: " << rFlags.data.size() << ')';
    IndexPartition<>(rContainer.size()).for_each([&rContainer, &rFlags, mask](std::size_t i_item) mutable {
        Flags source = rFlags.data[i_item];
        Flags& r_target = *(rContainer.begin() + i_item);
        Flags tmp = r_target & mask;
        mask.Flip(Flags::AllDefined());
        r_target = (source & mask) | tmp;
    });
}


template <class TValue, class TClass>
void DefineDynamicEntityProxyMembers(TClass& rPythonClass)
{
    rPythonClass
        .def("HasValue",
             &WRApp::DynamicEntityProxy::HasValue<Variable<TValue>>,
             pybind11::arg("variable"))
        .def("GetValue",
             [](const WRApp::DynamicEntityProxy Self, const Variable<TValue>& rVariable){return Self.GetValue(rVariable);},
             pybind11::arg("variable"))
        .def("SetValue",
             &WRApp::DynamicEntityProxy::SetValue<Variable<TValue>>,
             pybind11::arg("variable"),
             pybind11::arg("new_value"))
        ;
}


} // namespace


void AddUtilsToPython(pybind11::module& rModule)
{
    auto utils = rModule.def_submodule("Utils");

    utils.def("GetGlobalFlagNames",
              GetComponentNames<Flags>,
              "Get a list of all registered global flag names.");

    utils.def("GetDataValueContainerKeys",
              [](const DataValueContainer& rContainer) {
                        pybind11::list names;
                        for (const auto& r_name : WRApp::DataValueContainerKeyRange(rContainer.begin(), rContainer.end()))
                            names.append(r_name);
                        return names;
                    },
              pybind11::arg("data_value_container"),
              "Construct a list of variables' names in a DataValueContainer.");

    pybind11::class_<FlagArray>(utils, "FlagArray")
        .def(pybind11::init<>())
        ;

    #define KRATOS_DEFINE_FLAG_EXTRACTOR(CONTAINER_TYPE)        \
        utils.def("GetFlags",                                   \
                  &GetFlags<CONTAINER_TYPE>,                    \
                  pybind11::arg("container"),                   \
                  pybind11::arg("mask") = Flags::AllDefined(),  \
                  "Convert items in a container to flags.");    \
        utils.def("SetFlags",                                   \
                  &SetFlags<CONTAINER_TYPE>,                    \
                  pybind11::arg("target_container"),            \
                  pybind11::arg("source_flags"),                \
                  pybind11::arg("mask") = Flags::AllDefined(),  \
                  "Convert items in a container to flags.");

    KRATOS_DEFINE_FLAG_EXTRACTOR(ModelPart::NodesContainerType);
    KRATOS_DEFINE_FLAG_EXTRACTOR(ModelPart::ElementsContainerType);
    KRATOS_DEFINE_FLAG_EXTRACTOR(ModelPart::ConditionsContainerType);
    #undef KRATOS_DEFINE_FLAG_EXTRACTOR

    pybind11::class_<WRApp::ModelPredicate, WRApp::ModelPredicate::Pointer, ModelPredicateTrampoline>(rModule, "ModelPredicate")
        .def("__call__", &WRApp::ModelPredicate::operator())
        ;

    pybind11::class_<WRApp::WRAppClass, WRApp::WRAppClass::Pointer, WRAppClassTrampoline>(rModule, "WRAppClass")
        .def(pybind11::init<>())
        .def("GetDefaultParameters", &WRApp::WRAppClass::GetDefaultParameters)
        ;

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
        .def("Glob",
             &Glob,
             "Collect all file/directory paths that match the pattern.")
        .def("GetPatternString",
             &PlaceholderPattern::GetPatternString,
             "Get the placeholder pattern the object was constructed with.")
        .def("GetRegexString",
             &PlaceholderPattern::GetRegexString,
             "Get the string representation of the regex.")
        .def("IsConst",
             &PlaceholderPattern::IsConst,
             "Return true if the input pattern contains no placeholders.")
        .def_property_static("Integer",
                             [](Ref<const pybind11::object>) {return RegexUtility::Integer().first;},
                             [](Ref<pybind11::object>, Ref<const std::string>) {KRATOS_ERROR << "PlaceholderPattern::Integer is immutable";})
        .def_property_static("UnsignedInteger",
                             [](Ref<const pybind11::object>) {return RegexUtility::UnsignedInteger().first;},
                             [](Ref<pybind11::object>, Ref<const std::string>) {KRATOS_ERROR << "PlaceholderPattern::UnsignedInteger is immutable";})
        .def_property_static("FloatingPoint",
                             [](Ref<const pybind11::object>) {return RegexUtility::FloatingPoint().first;},
                             [](Ref<pybind11::object>, Ref<const std::string>) {KRATOS_ERROR << "PlaceholderPattern::FloatingPoint is immutable";})
        .def(pybind11::pickle([](Ref<const PlaceholderPattern> rPattern) -> pybind11::tuple {
                                  return pybind11::make_tuple(rPattern.GetPatternString(),
                                                              rPattern.GetPlaceholderMap());
                              },
                              [](pybind11::tuple Arguments) -> PlaceholderPattern {
                                  KRATOS_ERROR_IF_NOT(Arguments.size() == 2)
                                      << "Failed to deserialize PlaceholderPattern. Expecting exactly 2 arguments:"
                                      << "\n\t0:pattern_string"
                                      << "\n\t1:placeholder_map"
                                      << "\nbut got " << Arguments;
                                  return PlaceholderPattern(Arguments[0].cast<std::string>(),
                                                          Arguments[1].cast<PlaceholderPattern::PlaceholderMap>());
                              }))
        ;

    pybind11::class_<ModelPartPattern, ModelPartPattern::Pointer, PlaceholderPattern>(rModule, "ModelPartPattern")
        .def(pybind11::init<const std::string&>())
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
        .def("__hash__", [](WRApp::CheckpointID& rSelf) {return std::hash<WRApp::CheckpointID>()(rSelf);})
        .def("__repr__", [](const WRApp::CheckpointID& rThis) {
                std::stringstream stream;
                stream << rThis;
                return stream.str();
            })
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

    auto dynamic_entity_proxy = pybind11::class_<WRApp::DynamicEntityProxy>(rModule, "EntityProxy");
    dynamic_entity_proxy
        .def(pybind11::init<Globals::DataLocation,Node&>(),
             pybind11::arg("data_location"),
             pybind11::arg("entity"))
        .def(pybind11::init<Globals::DataLocation,Element&>(),
             pybind11::arg("data_location"),
             pybind11::arg("entity"))
        .def(pybind11::init<Globals::DataLocation,Condition&>(),
             pybind11::arg("data_location"),
             pybind11::arg("entity"))
        .def(pybind11::init<Globals::DataLocation,ProcessInfo&>(),
             pybind11::arg("data_location"),
             pybind11::arg("entity"))
        .def(pybind11::init<Globals::DataLocation,ModelPart&>(),
             pybind11::arg("data_location"),
             pybind11::arg("entity"))
        ;
    DefineDynamicEntityProxyMembers<bool>(dynamic_entity_proxy);
    DefineDynamicEntityProxyMembers<int>(dynamic_entity_proxy);
    DefineDynamicEntityProxyMembers<double>(dynamic_entity_proxy);
    DefineDynamicEntityProxyMembers<array_1d<double,3>>(dynamic_entity_proxy);
    DefineDynamicEntityProxyMembers<array_1d<double,4>>(dynamic_entity_proxy);
    DefineDynamicEntityProxyMembers<array_1d<double,6>>(dynamic_entity_proxy);
    DefineDynamicEntityProxyMembers<array_1d<double,9>>(dynamic_entity_proxy);
    DefineDynamicEntityProxyMembers<Vector>(dynamic_entity_proxy);
    DefineDynamicEntityProxyMembers<DenseMatrix<double>>(dynamic_entity_proxy);
}


} // namespace Kratos::Python
