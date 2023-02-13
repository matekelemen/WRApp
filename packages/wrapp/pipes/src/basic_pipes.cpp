/// @author Máté Kelemen

// --- WRApplication Includes ---
#include "wrapp/pipes/inc/basic_pipes.hpp"


namespace Kratos::Pipes {


ModelPartFromModel::ModelPartFromModel(std::string&& rModelPartName) noexcept
    : mModelPartName(std::move(rModelPartName))
{
}


ModelPartFromModel::ModelPartFromModel(const std::string& rModelPartName)
    : mModelPartName(rModelPartName)
{
}


ModelPartFromModel::ModelPartFromModel(const Parameters& rParameters)
    : mModelPartName()
{
    KRATOS_ERROR_IF_NOT(rParameters.Has("model_part_name"))
        << "ModelPartFromModel requires a \"model_part_name\" entry in the input parameters but found none in:\n"
        << rParameters;

    const auto model_part_name = rParameters["model_part_name"];
    KRATOS_ERROR_IF_NOT(model_part_name.IsString()) << "ModelPartFromModel expects \"model_part_name\" as a string, but got\n"
        << model_part_name;

    mModelPartName = model_part_name.GetString();
}


Parameters ModelPartFromModel::GetDefaultParameters()
{
    return Parameters(R"({"model_part_name" : ""})");
}


Parameters ProcessInfoFromModelPart::GetDefaultParameters()
{
    return Parameters();
}


TimeFromProcessInfo::TimeFromProcessInfo()
    : VariableFromProcessInfo<decltype(TIME)>(TIME)
{
}


TimeFromProcessInfo::TimeFromProcessInfo(const Parameters& rParameters)
    : TimeFromProcessInfo()
{
}


StepFromProcessInfo::StepFromProcessInfo()
    : VariableFromProcessInfo<decltype(STEP)>(STEP)
{
}


StepFromProcessInfo::StepFromProcessInfo(const Parameters& rParameters)
    : StepFromProcessInfo()
{
}


template <class TInput>
ConstPredicate<TInput>::ConstPredicate() noexcept
    : ConstPredicate(false)
{
}


template <class TInput>
ConstPredicate<TInput>::ConstPredicate(bool value) noexcept
    : mValue(value)
{
}


template <class TInput>
ConstPredicate<TInput>::ConstPredicate(const Parameters& rParameters)
    : ConstPredicate()
{
    KRATOS_ERROR_IF_NOT(rParameters.Has("value") && rParameters["value"].Is<bool>())
        << "Expecting parameters with a boolean entry for 'value', but got "
        << rParameters;

    this->mValue = rParameters["value"].Get<bool>();
}


template <class TInput>
Parameters ConstPredicate<TInput>::GetDefaultParameters()
{
    return Parameters(R"({"value" : false})");
}


template class ConstPredicate<const Model&>;


} // namespace Kratos::Pipes
