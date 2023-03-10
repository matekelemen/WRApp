//    |  /           |
//    ' /   __| _` | __|  _ \   __|
//    . \  |   (   | |   (   |\__ `
//   _|\_\_|  \__,_|\__|\___/ ____/
//                   Multi-Physics
//
//  License:         BSD License
//                   license: HDF5Application/license.txt
//
//  Main author:     Máté Kelemen
//

#pragma once

// Core includes
#include "containers/model.h"
#include "includes/define.h"


namespace Kratos::WRApp {


/// @brief Base class for functors that take a @ref Model and return a bool.
struct KRATOS_API(WRApplication) ModelPredicate
{
    KRATOS_CLASS_POINTER_DEFINITION(ModelPredicate);

    virtual ~ModelPredicate() {}

    virtual bool operator()(const Model& rModel) const = 0;
}; // struct ModelPredicate


} // namespace Kratos::WRApp
