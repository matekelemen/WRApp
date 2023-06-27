/// @author Máté Kelemen

#pragma once

// --- Core Includes ---
#include "containers/data_value_container.h"
#include "includes/kratos_export_api.h"

// --- WRApp Includes ---
#include "wrapp/utils/inc/Range.hpp"

// --- STL Includes ---
#include <type_traits>


namespace Kratos::WRApp {


/// @addtogroup WRApplication
/// @{
/// @addtogroup utilities
/// @{


/**
 *  @brief Iterator providing access to variables' names within a @ref DataValueContainer.
 *  @tparam TIterator Iterator type of the map.
 */
class KRATOS_API(WR_APPLICATION) DataValueContainerKeyIterator
{
private:
    using Wrapped = DataValueContainer::const_iterator;

public:
    using value_type = std::string;

    /// const key_type* if const_iterator else key_type*
    using pointer = const value_type*;

    /// const key_type& if const_iterator else key_type&
    using reference = const value_type&;

    using difference_type = Wrapped::difference_type;

    using iterator_category = std::forward_iterator_tag;

    DataValueContainerKeyIterator() = default;

    DataValueContainerKeyIterator(Wrapped wrapped)
        : mWrapped(wrapped)
    {}

    DataValueContainerKeyIterator(DataValueContainerKeyIterator&& rOther) noexcept = default;

    DataValueContainerKeyIterator(const DataValueContainerKeyIterator& rOther) noexcept = default;

    reference operator*()
    {return mWrapped->first->Name();}

    pointer operator->()
    {return &mWrapped->first->Name();}

    DataValueContainerKeyIterator& operator++()
    {++mWrapped; return *this;}

    DataValueContainerKeyIterator operator++(int)
    {DataValueContainerKeyIterator copy(*this); ++(*this); return copy;}

    friend bool operator==(DataValueContainerKeyIterator Left, DataValueContainerKeyIterator Right)
    {return Left.mWrapped == Right.mWrapped;}

    friend bool operator!=(DataValueContainerKeyIterator Left, DataValueContainerKeyIterator Right)
    {return !(Left == Right);}

private:
    Wrapped mWrapped;
}; // class DataValueContainerKeyIterator



/// @brief Range class iterating over the variable names within a @ref DataValueContainer
using DataValueContainerKeyRange = Range<DataValueContainerKeyIterator>;


/// @}
/// @}


} // namespace Kratos::WRApp
