/// @author Máté Kelemen

#pragma once

// --- Core Includes ---
#include "includes/define.h"
#include "includes/kratos_parameters.h"


namespace Kratos::WRApp {

namespace Impl {


/// @addtogroup WRApplication
/// @{
/// @addtogroup numeric
/// @{

/**
 *  @brief Utility class for membership tests on a 1D interval.
 *  @note This class template has specializations for @a double and @a int but is not implemented for other types.
 */
template <class TValue>
class KRATOS_API(WR_APPLICATION) IntervalUtility
{
public:

    KRATOS_CLASS_POINTER_DEFINITION(IntervalUtility);

    /// Default constructor initializing boundaries to "Begin" and "End".
    IntervalUtility();

    /**
     *  @brief Construct from parameters containing "interval".
     *
     *  @details "interval" is expected as an array with exactly 2 items, defining
     *           the begin and end of the interval respectively. The first item can
     *           either be a numeric value or "Begin" (setting the smallest representable
     *           value of @a TValue), while the second one can be a numeric value or
     *           "End" (setting the highest representable value of @a TValue).
     *
     *  @note String values ("Begin" and "End") are replaced with their numeric counterparts
     *        in the input @a Settings.
     *
     *  @note If "interval" is not in @a Settings, an "interval" with values corresponding
     *        to "Begin" and "End" is added to it.
     *
     *  @note Other parameters in @a Settings are not checked.
     *
     *  @throws If @a Settings has "interval" but has invalid value:
     *          - not an array of size 2
     *          - first item is not "Begin" or an appropriate numeric value
     *          - second item is not "End" or an appropriate numeric value
     *          - swapped boundaries (end < begin)
     */
    IntervalUtility(Parameters Settings);

    IntervalUtility(IntervalUtility&& rOther) = default;

    IntervalUtility(const IntervalUtility& rOther) = default;

    TValue GetIntervalBegin() const noexcept;

    TValue GetIntervalEnd() const noexcept;

    /// @brief Check whether the input value is within the defined closed interval [Begin, End].
    bool IsInInterval(TValue Value) const noexcept;

    static Parameters GetDefaultParameters();

    /// Return information as a string.
    std::string Info() const;

    /// Print information about this object.
    void PrintInfo(std::ostream& rOStream) const;

    /// Print object's data.
    void PrintData(std::ostream& rOStream) const;

private:
    /**
     *  @brief Set the boundaries from numeric values in the input @a parameters.
     *
     *  @details This member has explicit specializations for different types
     *           that may slightly adjust the interval boundaries
     *           (eg.: introduce floating point round-off tolerance).
     *           Check the specializations for the exact behaviour.
     */
    void SetBoundaries(TValue begin, TValue end) noexcept;

    TValue mBegin;

    TValue mEnd;
};


/// output stream function
template <class TValue>
std::ostream& operator << (std::ostream& rOStream, const IntervalUtility<TValue>& rThis)
{
    rThis.PrintInfo(rOStream);
    rOStream << " : ";
    rThis.PrintData(rOStream);
    return rOStream;
}


/// @}
/// @}


} // namespace Impl


/// @addtogroup WRApplication
/// @{
/// @addtogroup numeric
/// @{

/// A class providing membership tests on 1D rational intervals (eg.: time intervals).
using IntervalUtility = Impl::IntervalUtility<double>;

/// A class providing membership tests on 1D integer intervals (eg.: step intervals).
using DiscreteIntervalUtility = Impl::IntervalUtility<int>;


/// @}
/// @}

} // namespace Kratos
