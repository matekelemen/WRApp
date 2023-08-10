/// @author Máté Kelemen

#pragma once

// --- Core Includes ---
#include "includes/global_variables.h" // Globals::DataLocation
#include "includes/model_part.h" // ModelPart::NodesContainerType, ModelPart::ElementsContainerType, ModelPart::ConditionsContainerType
#include "includes/kratos_export_api.h" // KRATOS_API

// --- WRApp Includes ---
#include "wrapp/utils/inc/EntityProxy.hpp" // EntityProxy

// --- STL Includes ---
#include <variant> // variant


namespace Kratos::WRApp {


/// @addtogroup WRApplication
/// @{
/// @addtogroup utilities
/// @{


/// @brief Runtime version of @ref EntityProxy.
class KRATOS_API(WR_APPLICATION) DynamicEntityProxy
{
public:
    DynamicEntityProxy() noexcept = default;

    template <Globals::DataLocation TLocation>
    DynamicEntityProxy(EntityProxy<TLocation,true> Proxy) noexcept : mProxy(Proxy) {}

    DynamicEntityProxy(Globals::DataLocation Location, Node& rNode);

    DynamicEntityProxy(Globals::DataLocation Location, Element& rElement);

    DynamicEntityProxy(Globals::DataLocation Location, Condition& rCondition);

    DynamicEntityProxy(Globals::DataLocation Location, ProcessInfo& rProcessInfo);

    DynamicEntityProxy(Globals::DataLocation Location, ModelPart& rModelPart);

    template <class TVariable>
    bool HasValue(const TVariable& rVariable) const
    {
        KRATOS_TRY
        return std::visit(
            [&rVariable](auto Proxy){
                return Proxy.HasValue(rVariable);
            },
            mProxy
        );
        KRATOS_CATCH("")
    }

    template <class TVariable>
    typename TVariable::Type GetValue(const TVariable& rVariable) const
    {
        KRATOS_TRY
        return std::visit(
            [&rVariable](auto Proxy){
                return Proxy.GetValue(rVariable);
            },
            mProxy
        );
        KRATOS_CATCH("")
    }

    template <class TVariable>
    typename TVariable::Type& GetValue(const TVariable& rVariable)
    {
        KRATOS_TRY
        return std::visit(
            [&rVariable](auto Proxy){
                return Proxy.GetValue(rVariable);
            },
            mProxy
        );
        KRATOS_CATCH("")
    }

    template <class TVariable>
    void SetValue(const TVariable& rVariable, const typename TVariable::Type& rValue) const
    {
        KRATOS_TRY
        return std::visit(
            [&rVariable, &rValue](auto Proxy){
                return Proxy.SetValue(rVariable, rValue);
            },
            mProxy
        );
        KRATOS_CATCH("")
    }

private:
    std::variant<
        EntityProxy<Globals::DataLocation::NodeHistorical,true>,
        EntityProxy<Globals::DataLocation::NodeNonHistorical,true>,
        EntityProxy<Globals::DataLocation::Element,true>,
        EntityProxy<Globals::DataLocation::Condition,true>,
        EntityProxy<Globals::DataLocation::ProcessInfo,true>,
        EntityProxy<Globals::DataLocation::ModelPart,true>
    > mProxy;
}; // class DynamicEntityProxy


/// @}
/// @}


} // namespace Kratos::WRApp
