/// @author Máté Kelemen

#pragma once

// --- WRApp Includes ---
#include "basic_pipes.hpp"
#include "wrapp/pipes/inc/basic_pipes.hpp"
#include "wrapp/utils/inc/WRAppClass.hpp"
#include "wrapp/utils/inc/ModelPredicate.hpp"

// --- Core Includes ---
#include "includes/smart_pointers.h"
#include "includes/model_part.h"
#include "includes/kratos_parameters.h"
#include "utilities/interval_utility.h"

// --- STL Includes ---
#include <functional> // std::less


namespace Kratos::WRApp {


/// @addtogroup WRApplication
/// @{
/// @addtogroup pipes
/// @{


template <class TPipe>
class KRATOS_API(WR_APPLICATION) ModelPredicatePipe
    : public WRApp::ModelPredicate,
      public Pipes::Traits<const Model&, bool>,
      public WRAppClass
{
public:
    KRATOS_CLASS_POINTER_DEFINITION(ModelPredicatePipe);

    ModelPredicatePipe()
        : mPipe()
    {}

    ModelPredicatePipe(const Parameters& rParameters)
        : mPipe(rParameters)
    {}

    ModelPredicatePipe(ModelPredicatePipe&& rOther) noexcept = default;

    ModelPredicatePipe(const ModelPredicatePipe& rOther) = default;

    bool operator()(const Model& rModel) const override
    {return mPipe(rModel);}

    virtual Parameters GetDefaultParameters() const override
    {return TPipe::GetDefaultParameters();}

private:
    TPipe mPipe;
}; // class ModelPredicatePipe


/** @brief Always returns the boolean value it was constructed with, regardless of the input @ref Model.
 *  @details @code Model => true/false @endcode.
 *           Required parameters:
 *           @code
 *           [
 *               {"value" : <bool>}
 *           ]
 *           @endcode
 */
using ConstModelPredicate = ModelPredicatePipe<Pipes::SingleSegmentPipeline<
    Pipes::ConstPredicate<const Model&>
>>;


/** @brief Check whether @ref TIME is greater than the provided value.
 *  @details @code Model => ModelPart => ProcessInfo => TIME => std::less @endcode.
 *           Default parameters:
 *           @code
 *           [
 *              {"model_part_name" : ""},   // <== model part from model
 *              {},                         // <== process info from model part
 *              {},                         // <== time from process info
 *              {"rhs" : 0}                 // <== double comparison
 *           ]
 *           @code
 */
using TimeGreaterPredicate = ModelPredicatePipe<Pipes::Pipeline<
    Pipes::ModelPartFromModel,
    Pipes::ProcessInfoFromModelPart,
    Pipes::TimeFromProcessInfo,
    Pipes::Comparison<double,std::greater<double>>
>>;


/**
 *  @brief Check whether @ref TIME in a @ref ModelPart is within an interval.
 *  @details Model => ModelPart => ProcessInfo => TIME => IntervalUtility::IsIninterval.
 *           Required parameters (other settings ignored):
 *           @code
 *           [
 *              {"model_part_name" : ""},           // <== model part from model
 *              {},                                 // <== process info from model part
 *              {},                                 // <== time from process info
 *              {"interval" : ["Begin", "End"]}     // <== interval utility
 *           ]
 *           @endcode
 *  @note See @ref IntervalUtility for details.
 */
using TimeIntervalPredicate = ModelPredicatePipe<Pipes::Pipeline<
    Pipes::ModelPartFromModel,
    Pipes::ProcessInfoFromModelPart,
    Pipes::TimeFromProcessInfo,
    Pipes::IntervalPredicate<double>
>>;


/**
 *  @brief Check whether @ref STEP in a @ref ModelPart is within an interval.
 *
 *  @details @code Model => ModelPart => ProcessInfo => STEP => DiscreteIntervalUtility::IsIninterval @endcode.
 *           Required parameters (other settings ignored):
 *           @code
 *           [
 *              {"model_part_name" : ""},           // <== model part from model
 *              {},                                 // <== process info from model part
 *              {},                                 // <== step from process info
 *              {"interval" : ["Begin", "End"]}     // <== discrete interval utility
 *           ]
 *           @endcode
 *
 *  @note See @ref DiscreteIntervalUtility for details.
 */
using StepIntervalPredicate = ModelPredicatePipe<Pipes::Pipeline<
    Pipes::ModelPartFromModel,
    Pipes::ProcessInfoFromModelPart,
    Pipes::StepFromProcessInfo,
    Pipes::IntervalPredicate<int>
>>;


/**
 *  @brief Check whether @ref TIME in a @ref ModelPart is within a cyclic interval.
 *
 *  @details @code Model => ModelPart => ProcessInfo => TIME => Add => Modulo => IntervalUtility::IsInInterval @endcode.
 *           Required parameters (other settings ignored):
 *           @code
 *           [
 *              {"model_part_name" : ""},           // <== model part from model
 *              {},                                 // <== process info from model part
 *              {},                                 // <== time from process info
 *              {"value" : 0},                      // <== apply an offset
 *              {"mod" : 0},                        // <== modulo
 *              {"interval" : ["Begin", "End"]}     // <== interval utility
 *           ]
 *           @endcode
 *
 *           Example with @code {"mod" : 12.0, "interval" : [3.0, 6.0]} @endcode
 *           @code
 *           TIME:   12          24          36          48          60
 *           ... ----|-----------|-----------|-----------|-----------|---- ...
 *                      ++++        ++++        ++++        ++++        ++
 *           @endcode
 *
 *  @note See @ref IntervalUtility for details.
 *  @note The offset can be used to handle tricky cases with module and floating point representations.
 */
 using PeriodicTimeIntervalPredicate = ModelPredicatePipe<Pipes::Pipeline<
    Pipes::ModelPartFromModel,
    Pipes::ProcessInfoFromModelPart,
    Pipes::TimeFromProcessInfo,
    Pipes::Add<double>,
    Pipes::Modulo<double>,
    Pipes::IntervalPredicate<double>
>>;


/**
 *  @brief Check whether @ref STEP in a @ref ModelPart is within a cyclic interval.
 *
 *  @details @code Model => ModelPart => ProcessInfo => STEP => Modulo => DiscreteIntervalUtility::IsInInterval @endcode.
 *           Required parameters (other settings ignored):
 *           @code
 *           [
 *              {"model_part_name" : ""},           // <== model part from model
 *              {},                                 // <== process info from model part
 *              {},                                 // <== step from process info
 *              {"mod" : 0},                        // <== modulo
 *              {"interval" : ["Begin", "End"]}     // <== interval utility
 *           ]
 *           @endcode
 *
 *           Example with @code {"mod" : 12, "interval" : [3, 6]} @endcode
 *           @code
 *           TIME:   12          24          36          48          60
 *           ... ----|-----------|-----------|-----------|-----------|---- ...
 *                      ++++        ++++        ++++        ++++        ++
 *           @endcode
 *
 *  @note See @ref DiscreteIntervalUtility for details.
 */
 using PeriodicStepIntervalPredicate = ModelPredicatePipe<Pipes::Pipeline<
    Pipes::ModelPartFromModel,
    Pipes::ProcessInfoFromModelPart,
    Pipes::StepFromProcessInfo,
    Pipes::Modulo<int>,
    Pipes::IntervalPredicate<int>
>>;


/// @}
/// @}


} // namespace Kratos::WRApp
