/// @author Máté Kelemen

#pragma once

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
 *  @brief Iterator providing access to the keys of an std::map or std::unordered_map.
 *  @tparam TIterator Iterator type of the map.
 */
template <class TIterator>
class MapKeyIterator
{
public:
    using value_type = typename TIterator::value_type::first_type;

    /// const key_type* if const_iterator else key_type*
    using pointer = typename std::conditional<Detail::IsConstIterator<TIterator>::value,const value_type*,value_type*>::type;

    /// const key_type& if const_iterator else key_type&
    using reference = typename std::conditional<Detail::IsConstIterator<TIterator>::value,const value_type&,value_type&>::type;

    using difference_type = typename TIterator::difference_type;

    using iterator_category = std::forward_iterator_tag;

    MapKeyIterator() = default;

    MapKeyIterator(TIterator Wrapped)
        : mWrapped(Wrapped)
    {}

    MapKeyIterator(MapKeyIterator&& rOther) noexcept = default;

    MapKeyIterator(const MapKeyIterator& rOther) noexcept = default;

    reference operator*()
    {return mWrapped->first;}

    pointer operator->()
    {return &mWrapped->first;}

    MapKeyIterator& operator++()
    {++mWrapped; return *this;}

    MapKeyIterator operator++(int)
    {MapKeyIterator copy(*this); ++(*this); return copy;}

    friend bool operator==(MapKeyIterator Left, MapKeyIterator Right)
    {return Left.mWrapped == Right.mWrapped;}

    friend bool operator!=(MapKeyIterator Left, MapKeyIterator Right)
    {return !(Left == Right);}

private:
    TIterator mWrapped;
}; // class MapKeyIterator



/**
 *  @brief Range class iterating over the keys of a standard-conforming map type.
 */
template <class TMap>
using MapKeyRange = Range<MapKeyIterator<typename TMap::const_iterator>>;


/**
 *  @brief Create a view on the keys of an std::map or std::unordered_map.
 *  @note This is a convenience function to avoid having to specify template parameters.
 */
template <class TMap>
MapKeyRange<TMap> MakeConstMapKeyRange(const TMap& rMap)
{
    return Range<MapKeyIterator<typename TMap::const_iterator>>(rMap.begin(), rMap.end());
}


/// @}
/// @}


} // namespace Kratos::WRApp
