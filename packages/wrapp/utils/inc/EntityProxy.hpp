/// @author Máté Kelemen

#pragma once

// --- Core Includes ---
#include "includes/global_variables.h" // DataLocation
#include "includes/kratos_export_api.h" // KRATOS_API
#include "includes/node.h" // Node
#include "includes/element.h" // Element
#include "includes/condition.h" // Condition
#include "utilities/variable_utils.h" // VariableUtils::HasValue, VariableUtils::GetValue, VariableUtils::SetValue

// --- WRApp Includes ---
#include "wrapp/utils/inc/OptionalRef.hpp" // OptionalRef

// --- STL Includes ---
#include <type_traits> // remove_reference_t, is_const_v, is_same_v, decay_t


namespace Kratos::WRApp {


template <class TEntityProxy>
class ContainerProxy;


/// @addtogroup WRApplication
/// @{
/// @addtogroup utilities
/// @{


/** @brief Wrapper class providing a uniform interface for historical/non-historical @ref Node, @ref Element, and @ref Condition.
 *  @details @ref EntityProxy exposes common functionality related accessing stored @ref Variable s within an entity,
 *         without additional runtime overhead. In this context, an entity can refer to:
 *         - a @ref Node with historical variables (@ref Globals::DataLocation::NodeHistorical)
 *         - a @ref Node with non-historical variables (@ref Globals::DataLocation::NodeNonHistorical)
 *         - an @ref Element (@ref Globals::DataLocation::Element)
 *         - a @ref Condition (@ref Globals::DataLocation::Condition)
 *         The exposed common functionalities include checking, reading and overwriting the values
 *         related to the provided variables associated with the entity.
 *  @warning Default constructed @ref EntityProxy instances are in an invalid state,
 *           and their member functions must not be called.
 *  @throws if member functions of a default constructed instance are called.
 */
template <Globals::DataLocation TLocation, bool TMutable>
class KRATOS_API(WR_APPLICATION) EntityProxy
{
private:
    constexpr static Globals::DataLocation Location = TLocation;

    constexpr static bool IsMutable = TMutable;

    /// @ref Node, @ref Element, or @ref Condition without a const-qualifier, depending on @a TLocation.
    using UnqualifiedEntity = std::conditional_t<
        TLocation == Globals::DataLocation::NodeHistorical || TLocation == Globals::DataLocation::NodeNonHistorical,
        Node,
        std::conditional_t<
            TLocation == Globals::DataLocation::Element,
            Element,
            std::conditional_t<
                TLocation == Globals::DataLocation::Condition,
                Condition,
                std::conditional_t<
                    TLocation == Globals::DataLocation::ProcessInfo,
                    ProcessInfo,
                    std::conditional_t<
                        TLocation == Globals::DataLocation::ModelPart,
                        ModelPart,
                        void // <== invalid fallback type; will throw a compile-time error
                    >
                >
            >
        >
    >;

    /// Const-qualified @ref Node, @ref Element, or @ref Condition, depending on @a TLocation and @a TMutable.
    using QualifiedEntity = std::conditional_t<TMutable,
                                               UnqualifiedEntity,
                                               const UnqualifiedEntity>;

    /// @ref ContainerProxy needs to access private typedefs.
    friend class ContainerProxy<EntityProxy>;

public:
    /// @brief Default constructor that leaves the instance in an invalid state.
    /// @throws if any member function is called without reassigning this instance
    ///         with a valid one.
    EntityProxy() noexcept = default;

    /// @brief Constructor creating a valid proxy, wrapping the input entity.
    /// @param rEntity Entity that will be accessed when member functions are called.
    /// @warning This proxy is invalidated when the container holding @a rEntity
    ///          invalidates its iterators or when @a rEntity is destroyed.
    EntityProxy(QualifiedEntity& rEntity) noexcept : mrEntity(rEntity) {}

    /// @brief Check whether the entity has a value for the provided variable.
    template <class TValue>
    bool HasValue(const Variable<TValue>& rVariable) const noexcept
    {
        return VariableUtils::HasValue<TLocation>(mrEntity.value(), rVariable);
    }

    /// @brief Fetch the value corresponding to the input variable in the wrapped entity.
    template <class TValue>
    std::conditional_t<std::is_integral_v<TValue> || std::is_floating_point_v<TValue>,
                       TValue,           // <== return by value if scalar type
                       const TValue&>    // <== return by reference in non-scalar type
    GetValue(const Variable<TValue>& rVariable) const
    {
        return VariableUtils::GetValue<TLocation>(mrEntity.value(), rVariable);
    }

    /// @brief Fetch the value corresponding to the input variable in the wrapped entity.
    template <class TValue, std::enable_if_t</*this is required for SFINAE*/!std::is_same_v<TValue,void> && TMutable,bool> = true>
    TValue& GetValue(const Variable<TValue>& rVariable)
    {
        return VariableUtils::GetValue<TLocation>(mrEntity.value(), rVariable);
    }

    /// @brief Overwrite the value corresponding to the input variable in the wrapped entity.
    template <class TValue, std::enable_if_t</*this is required for SFINAE*/!std::is_same_v<TValue,void> && TMutable,bool> = true>
    void SetValue(const Variable<TValue>& rVariable,
                  std::conditional_t<std::is_integral_v<TValue> || std::is_floating_point_v<TValue>,
                                     TValue,         /*pass scalar types by value*/
                                     const TValue&>  /*pass non-scalar types by reference*/ Value)
    {
        VariableUtils::SetValue<TLocation>(mrEntity.value(), rVariable, Value);
    }

    /// @brief Immutable access to the wrapped entity.
    const UnqualifiedEntity& GetEntity() const
    {
        return mrEntity.value();
    }

    /// @brief Mutable or immutable access to the wrapped entity, depending on @a TMutable.
    QualifiedEntity& GetEntity()
    {
        return mrEntity.value();
    }

private:
    OptionalRef<QualifiedEntity> mrEntity;
}; // class EntityProxy



/// @brief Invalid template base to be specialized for valid template parameters.
template <Globals::DataLocation TLocation, class TEntity>
inline auto MakeProxy(const TEntity& rEntity)
{
    static_assert(std::is_same_v<TEntity,void>, "Invalid DataLocation-Entity combination");
}


/// @brief Invalid template base to be specialized for valid template parameters.
template <Globals::DataLocation TLocation, class TEntity>
inline auto MakeProxy(TEntity& rEntity)
{
    static_assert(std::is_same_v<TEntity,void>, "Invalid DataLocation-Entity combination");
}


#define WRAPP_DEFINE_ENTITY_PROXY_FACTORY(TLocation, TEntity)                                   \
    /** @brief Convenience function for constructing immutable @ref EntityProxy instances.*/    \
    template <>                                                                                 \
    inline auto MakeProxy<TLocation,TEntity>(const TEntity& rEntity)                            \
    {return EntityProxy<TLocation,false>(rEntity);}                                             \
    /** @brief Convenience function for constructing mutable @ref EntityProxy instances.*/      \
    template <>                                                                                 \
    inline auto MakeProxy<TLocation,TEntity>(TEntity& rEntity)                                  \
    {return EntityProxy<TLocation,true>(rEntity);}

WRAPP_DEFINE_ENTITY_PROXY_FACTORY(Globals::DataLocation::NodeHistorical, Node)

WRAPP_DEFINE_ENTITY_PROXY_FACTORY(Globals::DataLocation::NodeNonHistorical, Node)

WRAPP_DEFINE_ENTITY_PROXY_FACTORY(Globals::DataLocation::Element, Element)

WRAPP_DEFINE_ENTITY_PROXY_FACTORY(Globals::DataLocation::Condition, Condition)

WRAPP_DEFINE_ENTITY_PROXY_FACTORY(Globals::DataLocation::ProcessInfo, ProcessInfo)

WRAPP_DEFINE_ENTITY_PROXY_FACTORY(Globals::DataLocation::ModelPart, ModelPart)

#undef WRAPP_DEFINE_ENTITY_PROXY_FACTORY


/// @brief Convenience function for constructing a mutable @ref ProcessInfo proxy from a @ref ModelPart.
template <>
inline auto MakeProxy<Globals::DataLocation::ProcessInfo,ModelPart>(const ModelPart& rModelPart)
{
    return EntityProxy<Globals::DataLocation::ProcessInfo,false>(rModelPart.GetProcessInfo());
}


/// @brief Convenience function for constructing an immutable @ref ProcessInfo proxy from a @ref ModelPart.
template <>
inline auto MakeProxy<Globals::DataLocation::ProcessInfo,ModelPart>(ModelPart& rModelPart)
{
    return EntityProxy<Globals::DataLocation::ProcessInfo,true>(rModelPart.GetProcessInfo());
}


/// @}
/// @}


} // namespace Kratos::WRApp
