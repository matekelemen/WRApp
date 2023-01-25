/// @author Máté Kelemen

// --- WRApp Includes ---
#include "wrapp/pipes/inc/AddPipesToPython.hpp"
#include "wrapp/pipes/inc/PipedModelPredicate.hpp"


namespace Kratos::Python {


void AddPipesToPython(pybind11::module& rModule)
{
    #define KRATOS_DEFINE_PIPED_PREDICATE_BINDINGS(NAME)    \
        pybind11::class_<WRApp::NAME,                       \
                         WRApp::NAME::Pointer,              \
                         ModelPredicate>(rModule, #NAME)    \
            .def(pybind11::init<>())                        \
            .def(pybind11::init<const Parameters&>())       \
            .def("__call__", &WRApp::NAME::operator())

    KRATOS_DEFINE_PIPED_PREDICATE_BINDINGS(TimeIntervalPredicate);

    KRATOS_DEFINE_PIPED_PREDICATE_BINDINGS(StepIntervalPredicate);

    KRATOS_DEFINE_PIPED_PREDICATE_BINDINGS(PeriodicTimeIntervalPredicate);

    KRATOS_DEFINE_PIPED_PREDICATE_BINDINGS(PeriodicStepIntervalPredicate);

    #undef KRATOS_DEFINE_PIPED_PREDICATE_BINDINGS
}


} // namespace Kratos::Python
