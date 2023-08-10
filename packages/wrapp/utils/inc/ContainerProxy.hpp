/// @author Máté Kelemen

#pragma once

// --- Core Includes ---
#include "includes/global_variables.h" // DataLocation
#include "includes/kratos_export_api.h" // KRATOS_API
#include "includes/model_part.h" // ModelPart::NodesContainerType, ModelPart::ElementsContainerType, ModelPart::ConditionsContainerType
#include "utilities/model_part_utils.h" // ModelPartUtils::GetContainer

// --- WRApp Includes ---
#include "wrapp/utils/inc/EntityProxy.hpp" // EntityProxy


namespace Kratos::WRApp {


/** @brief A view with a uniform interface for @ref ModelPart::NodesContainerType, @ref ModelPart::ElementsContainerType, or @ref ModelPart::ConditionsContainerType.
 *  @details @ref ContainerProxy provides uniform access to the @ref Variable s stored in the entities of a container.
 *           Entities in the container are wrapped by @ref EntityProxy. In this context, an entity can refer to:
 *         - a @ref Node with historical variables (@ref Globals::DataLocation::NodeHistorical)
 *         - a @ref Node with non-historical variables (@ref Globals::DataLocation::NodeNonHistorical)
 *         - an @ref Element (@ref Globals::DataLocation::Element)
 *         - a @ref Condition (@ref Globals::DataLocation::Condition)
 */
template <class TEntityProxy>
class KRATOS_API(WR_APPLICATION) ContainerProxy
{
private:
    using UnqualifiedContainer = std::conditional_t<
        std::is_same_v<typename TEntityProxy::UnqualifiedEntity,Node>,
        ModelPart::NodesContainerType,
        std::conditional_t<
            std::is_same_v<typename TEntityProxy::UnqualifiedEntity,Element>,
            ModelPart::ElementsContainerType,
            std::conditional_t<
                std::is_same_v<typename TEntityProxy::UnqualifiedEntity,Condition>,
                ModelPart::ConditionsContainerType,
                void // <== invalid fallback type; will throw a compile-time error
            >
        >
    >;

    constexpr static bool IsMutable = TEntityProxy::IsMutable;

    using WrappedIterator = std::conditional_t<IsMutable,
                                               typename UnqualifiedContainer::iterator,
                                               typename UnqualifiedContainer::const_iterator>;

    template <bool TMutable>
    class Iterator
    {
    private:
        using Wrapped = std::conditional_t<TMutable,
                                           typename UnqualifiedContainer::iterator,
                                           typename UnqualifiedContainer::const_iterator>;

    public:
        using value_type = EntityProxy<TEntityProxy::Location,TMutable>;

        using pointer = std::conditional_t<TMutable,
                                           value_type*,
                                           const value_type*>;

        using reference = std::conditional_t<TMutable,
                                             value_type&,
                                             const value_type&>;

        using difference_type = std::ptrdiff_t;

        using iterator_category = std::random_access_iterator_tag;

        Iterator() noexcept = default;

        Iterator(Wrapped It) noexcept : mWrapped(It) {}

        value_type operator*() const noexcept {return value_type(*mWrapped);}

        Iterator& operator++() noexcept {++mWrapped; return *this;}

        Iterator operator++(int) noexcept {Iterator copy(mWrapped); ++mWrapped; return copy;}

        Iterator& operator--() noexcept {--mWrapped; return *this;}

        Iterator operator--(int) noexcept {Iterator copy(mWrapped); --mWrapped; return copy;}

        Iterator& operator+=(difference_type Rhs) noexcept {mWrapped += Rhs; return *this;}

        Iterator& operator-=(difference_type Rhs) noexcept {mWrapped -= Rhs; return *this;}

        Iterator operator+(difference_type Rhs) const noexcept {Iterator copy(mWrapped); copy += Rhs; return copy;}

        Iterator operator-(difference_type Rhs) const noexcept {Iterator copy(mWrapped); copy -= Rhs; return copy;}

        difference_type operator-(Iterator Rhs) const noexcept {return mWrapped - Rhs.mWrapped;}

        bool operator==(Iterator Rhs) const noexcept {return mWrapped == Rhs.mWrapped;}

        bool operator!=(Iterator Rhs) const noexcept {return mWrapped != Rhs.mWrapped;}

        bool operator<(Iterator Rhs) const noexcept {return mWrapped < Rhs.mWrapped;}

        bool operator>(Iterator Rhs) const noexcept {return mWrapped > Rhs.mWrapped;}

        bool operator<=(Iterator Rhs) const noexcept {return mWrapped <= Rhs.mWrapped;}

        bool operator>=(Iterator Rhs) const noexcept {return mWrapped >= Rhs.mWrapped;}

    private:
        Wrapped mWrapped;
    }; // class Iterator
public:
    using iterator = Iterator<IsMutable>;

    using const_iterator = Iterator<false>;

    using size_type = std::size_t;

    using value_type = typename iterator::value_type;

    ContainerProxy() noexcept = default;

    ContainerProxy(WrappedIterator Begin, WrappedIterator End) noexcept
        : mBegin(Begin),
          mEnd(End)
    {}

    typename const_iterator::value_type operator[](size_type Index) const noexcept {return typename const_iterator::value_type(*(mBegin + Index));}

    typename iterator::value_type operator[](size_type Index) noexcept {return typename iterator::value_type(*(mBegin + Index));}

    typename const_iterator::value_type at(size_type Index) const noexcept {return typename const_iterator::value_type(*(mBegin + Index));}

    typename iterator::value_type at(size_type Index) noexcept {return typename iterator::value_type(*(mBegin + Index));}

    size_type size() const noexcept {return std::distance(mBegin, mEnd);}

    bool empty() const noexcept {return this->size() == 0;}

    const_iterator cbegin() const noexcept {return const_iterator(mBegin);}

    const_iterator begin() const noexcept {return this->cbegin();}

    iterator begin() noexcept {return iterator(mBegin);}

    const_iterator cend() const noexcept {return const_iterator(mEnd);}

    const_iterator end() const noexcept {return this->cend();}

    iterator end() noexcept {return iterator(mEnd);}

private:
    WrappedIterator mBegin, mEnd;
}; // class ContainerProxy



#define WRAPP_DEFINE_CONTAINER_PROXY_FACTORY(TLocation)                                         \
    /** @brief Convenience function for constructing immutable @ref ContainerProxy instances.*/ \
    template <>                                                                                 \
    inline auto MakeProxy<TLocation,ModelPart>(const ModelPart& rModelPart)                     \
    {                                                                                           \
        const auto& r_container = ModelPartUtils::GetContainer<TLocation>(rModelPart);          \
        return ContainerProxy<EntityProxy<TLocation,false>>(r_container.begin(),                \
                                                            r_container.end());                 \
    }                                                                                           \
    /** @brief Convenience function for constructing mutable @ref ContainerProxy instances.*/   \
    template <>                                                                                 \
    inline auto MakeProxy<TLocation,ModelPart>(ModelPart& rModelPart)                           \
    {                                                                                           \
        auto& r_container = ModelPartUtils::GetContainer<TLocation>(rModelPart);                \
        return ContainerProxy<EntityProxy<TLocation,true>>(r_container.begin(),                 \
                                                           r_container.end());                  \
    }

WRAPP_DEFINE_CONTAINER_PROXY_FACTORY(Globals::DataLocation::NodeHistorical)

WRAPP_DEFINE_CONTAINER_PROXY_FACTORY(Globals::DataLocation::NodeNonHistorical)

WRAPP_DEFINE_CONTAINER_PROXY_FACTORY(Globals::DataLocation::Element)

WRAPP_DEFINE_CONTAINER_PROXY_FACTORY(Globals::DataLocation::Condition)

#undef WRAPP_DEFINE_CONTAINER_PROXY_FACTORY


} // namespace Kratos::WRApp
