/// @author Máté Kelemen

#pragma once

// --- Core Includes ---
#include "containers/variable.h"
#include "includes/process_info.h"
#include "containers/model.h"
#include "includes/model_part.h"
#include "includes/kratos_parameters.h"
#include "utilities/interval_utility.h"

// --- WRApplication Includes ---
#include "wrapp/pipes/inc/pipe.hpp"
#include "wrapp/numeric/inc/IntervalUtility.hpp"

// --- STL Includes ---
#include <optional>
#include <functional> // std::reference_wrapper
#include <cmath> // std::fmod


namespace Kratos::Pipes {


/// @addtogroup WRApplication
/// @{
/// @addtogroup pipes
/// @{


/// @brief Get a @ref ModelPart from a @ref Model by name.
/// @note Constructible from @ref Parameters with a "model_part_name" string entry.
class ModelPartFromModel : public Traits<const Model&, const ModelPart&>
{
public:
    ModelPartFromModel() = default;

    ModelPartFromModel(const std::string& rModelPartName);

    ModelPartFromModel(std::string&& rModelPartName) noexcept;

    ModelPartFromModel(const Parameters& rParameters);

    ModelPartFromModel(ModelPartFromModel&& rOther) noexcept = default;

    ModelPartFromModel(const ModelPartFromModel& rOther) = default;

    const ModelPart& operator()(const Model& rModel) const
    {return rModel.GetModelPart(mModelPartName);}

    static Parameters GetDefaultParameters();

private:
    std::string mModelPartName;
}; // class ModelPartFromModel


/// @brief Get the @ref ProcessInfo of a @ref ModelPart.
/// @note No-op constructible from @ref Parameters.
struct ProcessInfoFromModelPart : public Traits<const ModelPart&, const ProcessInfo&>
{
    ProcessInfoFromModelPart() noexcept = default;

    ProcessInfoFromModelPart(const Parameters& rParameters) noexcept {}

    ProcessInfoFromModelPart(ProcessInfoFromModelPart&& rOther) noexcept = default;

    ProcessInfoFromModelPart(const ProcessInfoFromModelPart& rOther) = default;

    const ProcessInfo& operator()(const ModelPart& rModelPart) const
    {return rModelPart.GetProcessInfo();}

    static Parameters GetDefaultParameters();
}; // struct ProcessInfoFromModelPart


/// @brief Get a variable from @ref ProcessInfo.
/// @note Constructible from @ref Parameters with a "process_info_variable" entry.
/// @warning This type is invalid if default-constructed.
template <class TVariable>
class VariableFromProcessInfo : public Traits<const ProcessInfo&, typename TVariable::Type>
{
public:
    VariableFromProcessInfo() = default;

    VariableFromProcessInfo(const TVariable& rVariable)
        : mVariable({rVariable})
    {}

    VariableFromProcessInfo(const Parameters& rParameters);

    VariableFromProcessInfo(VariableFromProcessInfo&& rOther) noexcept = default;

    VariableFromProcessInfo(const VariableFromProcessInfo& rOther) = default;

    typename TVariable::Type operator()(const ProcessInfo& rProcessInfo) const
    {
        KRATOS_ERROR_IF_NOT(bool(mVariable)) << "uninitialized variable in VariableFromProcessInfo";
        return rProcessInfo[mVariable.value().get()];
    }

    static Parameters GetDefaultParameters();

private:
    std::optional<std::reference_wrapper<const TVariable>> mVariable;
}; // class VariableFromProcessInfo


/// @brief Get @ref TIME from a @ref ProcessInfo.
/// @note Constructible from @ref Parameters without any requirements.
struct TimeFromProcessInfo : public VariableFromProcessInfo<decltype(TIME)>
{
    TimeFromProcessInfo();

    TimeFromProcessInfo(const Parameters& rParameters);

    TimeFromProcessInfo(TimeFromProcessInfo&& rOther) = default;

    TimeFromProcessInfo(const TimeFromProcessInfo& rOther) = default;
}; // struct TimeFromProcessInfo


/// @brief Get @ref STEP from a @ref ProcessInfo.
/// @note Constructible from @ref Parameters without any requirements.
struct StepFromProcessInfo : public VariableFromProcessInfo<decltype(STEP)>
{
    StepFromProcessInfo();

    StepFromProcessInfo(const Parameters& rParameters);

    StepFromProcessInfo(StepFromProcessInfo&& rOther) = default;

    StepFromProcessInfo(const StepFromProcessInfo& rOther) = default;
}; // struct TimeFromProcessInfo


/// @brief Perform a comparison operation on the input as the left hand side.
/// @note Constructible from @ref Parameters with an "rhs" entry.
template <class TValue, class TOperator>
class Comparison : public Traits<TValue,bool>
{
public:
    Comparison();

    Comparison(const Parameters& rParameters);

    bool operator()(TValue lhs) const noexcept;

    static Parameters GetDefaultParameters();

private:
    TValue mRHS;
}; // class Comparison


/// @brief Pipe wrapper for @ref Detail::IntervalUtility.
/// @note Constructible from @ref Parameters (passed on to @ref Detail::IntervalUtility).
template <class TValue>
class IntervalPredicate : public Traits<TValue,bool>
{
public:
    IntervalPredicate() = default;

    IntervalPredicate(TValue begin, TValue end);

    IntervalPredicate(const Parameters& rParameters);

    IntervalPredicate(IntervalPredicate&& rOther) noexcept = default;

    IntervalPredicate(const IntervalPredicate& rOther) = default;

    bool operator()(TValue Value) const
    {return mInterval.IsInInterval(Value);}

    static Parameters GetDefaultParameters();

private:
    WRApp::Impl::IntervalUtility<TValue> mInterval;
}; // class IntervalPredicate


/// @brief Compute the mod of the input.
/// @note Constructible from @ref Parameters with a "mod" entry (@a int or @a double).
template <class TValue>
class Modulo : public Traits<TValue,TValue>
{
public:
    Modulo() noexcept;

    Modulo(TValue modulo) noexcept;

    Modulo(const Parameters& rParameters);

    Modulo(Modulo&& rOther) noexcept = default;

    Modulo(const Modulo& rOther) = default;

    TValue operator()(TValue Value) const
    {
        if constexpr (std::is_integral_v<TValue>) {
            return Value % mModulo;
        } else {
            return std::fmod(Value, mModulo);
        }
    }

    static Parameters GetDefaultParameters();

private:
    TValue mModulo;
}; // class Modulo


/// @brief Add a constant value to the input.
/// @note Constructible from @ref Parameters with a "value" entry.
template <class TValue>
class Add : public Traits<TValue,TValue>
{
public:
    Add() noexcept;

    Add(TValue rhs) noexcept;

    Add(const Parameters& rParameters);

    TValue operator()(TValue input) const noexcept
    {
        return input + mValue;
    }

    static Parameters GetDefaultParameters();

private:
    TValue mValue;
}; // class Add


/// @brief Return a bool regardless of the input.
/// @details Constructible from @ref Parameters with a "value" entry (@a bool).
///          Defaults to @a false.
template <class TInput>
class ConstPredicate : public Traits<TInput,bool>
{
public:
    ConstPredicate() noexcept;

    ConstPredicate(bool value) noexcept;

    ConstPredicate(const Parameters& rParameters);

    ConstPredicate(ConstPredicate&& rOther) noexcept = default;

    ConstPredicate(const ConstPredicate& rOther) noexcept = default;

    bool operator()(TInput) const noexcept
    {return mValue;}

    static Parameters GetDefaultParameters();

private:
    bool mValue;
}; // class ConstPredicate


/// @}
/// @}


} // namespace Kratos::Pipes


// Template definitions
#include "wrapp/pipes/impl/basic_pipes_impl.hpp"
