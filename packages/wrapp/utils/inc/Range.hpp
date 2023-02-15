/// @author Máté Kelemen

#pragma once

// --- STL Includes ---
#include <iterator>
#include <type_traits>


namespace Kratos::WRApp {


/// @cond DETAIL


#define KRATOS_DEFINE_RANGE(ITERATOR_TYPE, CONST)                            \
{                                                                            \
public:                                                                      \
    using value_type = typename std::iterator_traits<TIterator>::value_type; \
    using pointer = typename std::iterator_traits<TIterator>::pointer;       \
    using reference = typename std::iterator_traits<TIterator>::reference;   \
    using size_type = std::size_t;                                           \
                                                                             \
    Range() : mBegin(), mEnd() {}                                            \
    Range(ITERATOR_TYPE begin, ITERATOR_TYPE end)                            \
        : mBegin(begin), mEnd(end) {}                                        \
    Range(Range&& rOther) noexcept = default;                                \
    Range(const Range& rOther) noexcept = default;                           \
                                                                             \
    ITERATOR_TYPE begin() CONST noexcept {return mBegin;}                    \
    ITERATOR_TYPE end() CONST noexcept {return mEnd;}                        \
    size_type size() const noexcept {return std::distance(mBegin, mEnd);}    \
    bool empty() const noexcept {return mBegin == mEnd;}                     \
                                                                             \
private:                                                                     \
    ITERATOR_TYPE mBegin;                                                    \
    ITERATOR_TYPE mEnd;                                                      \
}


/// @endcond


namespace Detail {
/// @cond DETAIL
template <class T>
struct IsConstPointer
{};


template <class T>
struct IsConstPointer<T*>
{static constexpr const bool value = false;};


template <class T>
struct IsConstPointer<const T*>
{static constexpr const bool value = true;};


template <class TIterator>
struct IsConstIterator
{
    static constexpr const bool value = IsConstPointer<typename std::iterator_traits<TIterator>::pointer>::value;
};
/// @endcond
} // namespace Detail


/// @addtogroup WRApplication
/// @{
/// @addtogroup utilities
/// @{


/**
 *  @brief Class representing a view into a subrange of a container.
 *  @tparam TIterator Iterator type of the target container.
 */
template <class TIterator, class IsConstRange = void>
class Range
KRATOS_DEFINE_RANGE(TIterator, ); // class Range (non-const version)


/**
 *  @brief Class representing a view into a subrange of an immutable container.
 *  @tparam TIterator Iterator type of the target container.
 */
template <class TIterator>
class Range<TIterator, typename std::enable_if<Detail::IsConstIterator<TIterator>::value>::type>
KRATOS_DEFINE_RANGE(TIterator, const); // class Range (const version)


/// @}
/// @}


#undef KRATOS_DEFINE_RANGE


} // namespace Kratos::WRApp
