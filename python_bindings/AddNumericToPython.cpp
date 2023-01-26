/// @author Máté Kelemen

// --- WRApplication Includes ---
#include "wrapp/numeric/inc/IntervalUtility.hpp"
#include "wrapp/numeric/inc/AddNumericToPython.hpp"


namespace Kratos::Python {


void AddNumericToPython(pybind11::module& rModule)
{
    #define KRATOS_DEFINE_INTERVAL_UTILITY_PYTHON_BINDINGS(CLASS_NAME)              \
        pybind11::class_<WRApplication::CLASS_NAME>(rModule, #CLASS_NAME)                   \
            .def(pybind11::init<>())                                                \
            .def(pybind11::init<Parameters>())                                      \
            .def("GetIntervalBegin", &WRApplication::CLASS_NAME ::GetIntervalBegin)         \
            .def("GetIntervalEnd", &WRApplication::CLASS_NAME ::GetIntervalEnd)             \
            .def("IsInInterval", &WRApplication::CLASS_NAME ::IsInInterval)                 \
            .def("GetDefaultParameters", &WRApplication::CLASS_NAME ::GetDefaultParameters) \
            .def("__str__", PrintObject<WRApplication::CLASS_NAME>)

    KRATOS_DEFINE_INTERVAL_UTILITY_PYTHON_BINDINGS(IntervalUtility);

    KRATOS_DEFINE_INTERVAL_UTILITY_PYTHON_BINDINGS(DiscreteIntervalUtility);

    #undef KRATOS_DEFINE_INTERVAL_UTILITY_PYTHON_BINDINGS
}


} // namespace Kratos::Python
