/// @author Máté Kelemen

#pragma once

// Included from "wrapp/pipes/inc/basic_pipes.h"
#include "wrapp/pipes/inc/basic_pipes.hpp" // unnecessary include to get language servers working

// --- STL Includes ---
#include <cmath>
#include <limits>


namespace Kratos::Pipes {


template <class TVariable>
VariableFromProcessInfo<TVariable>::VariableFromProcessInfo(const Parameters& rParameters)
{
    KRATOS_ERROR_IF_NOT(rParameters.Has("process_info_variable"))
        << "VariableFromProcessInfo expects a Parameters object with \"process_info_variable\", but got:\n"
        << rParameters;
    mVariable = rParameters["process_info_variable"].Get<typename TVariable::Type>();
}


template <class TVariable>
Parameters VariableFromProcessInfo<TVariable>::GetDefaultParameters()
{
    return Parameters();
}


template <class TValue, class TOperator>
Comparison<TValue,TOperator>::Comparison()
    : Comparison(Comparison::GetDefaultParameters())
{
}


template <class TValue, class TOperator>
Comparison<TValue,TOperator>::Comparison(const Parameters& rParameters)
    : mRHS(rParameters["rhs"].Get<TValue>())
{
}


template <class TValue, class TOperator>
bool Comparison<TValue,TOperator>::operator()(TValue lhs) const noexcept
{
    return TOperator()(lhs, mRHS);
}


template <class TValue, class TOperator>
Parameters Comparison<TValue,TOperator>::GetDefaultParameters()
{
    return Parameters(R"({"rhs" : 0})");
}


template <class TValue>
IntervalPredicate<TValue>::IntervalPredicate(TValue Begin, TValue End)
    : mInterval(Begin, End)
{
}


template <class TValue>
IntervalPredicate<TValue>::IntervalPredicate(const Parameters& rParameters)
    : mInterval(rParameters)
{
}


template <class TValue>
Parameters IntervalPredicate<TValue>::GetDefaultParameters()
{
    return WRApp::Impl::IntervalUtility<TValue>::GetDefaultParameters();
}


template <class TValue>
Modulo<TValue>::Modulo() noexcept
    : mModulo(std::numeric_limits<TValue>::max())
{
}


template <class TValue>
Modulo<TValue>::Modulo(const Parameters& rParameters)
{
    KRATOS_ERROR_IF_NOT(rParameters.Has("mod"))
        << "Modulo expects a Parameters object with a \"mod\" key, but got:\n"
        << rParameters;
    mModulo = rParameters["mod"].Get<TValue>();
}


template <>
inline double Modulo<double>::operator()(double Value) const
{
    return std::fmod(Value, mModulo);
}


template <class TValue>
Parameters Modulo<TValue>::GetDefaultParameters()
{
    Parameters parameters(R"({"mod" : 0})");
    parameters["mod"].Set<TValue>(std::numeric_limits<TValue>::max());
    return parameters;
}


} // namespace Kratos::Pipes
