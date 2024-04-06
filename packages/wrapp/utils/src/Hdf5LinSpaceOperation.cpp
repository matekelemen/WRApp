/// @author Máté Kelemen

// --- WRApp Includes ---
#include "wrapp/utils/inc/Hdf5LinSpaceOperation.hpp" // Hdf5LinSpaceOperation
#include "wrapp/utils/inc/common.hpp" // Ref

// --- HDF5 Includes ---
#include "custom_io/hdf5_file.h" // HDF5::File

// --- Core Includes ---
#include "utilities/parallel_utilities.h" // block_for_each, IndexPartition
#include "utilities/reduction_utilities.h" // MaxReduction
#include "includes/data_communicator.h" // DataCommunicator

// --- STL Includes ---
#include <filesystem> // filesystem::path
#include <string> // string


namespace Kratos::WRApp {


struct Hdf5LinSpaceOperation::Impl
{
    std::filesystem::path mFilePath;

    std::string mPrefix;

    std::size_t mBegin;

    std::size_t mStride;

    std::size_t mCount;

    bool mOverwrite;
}; // Hdf5LinSpaceOperation


Hdf5LinSpaceOperation::Hdf5LinSpaceOperation()
    : mpImpl(new Impl)
{
}


Hdf5LinSpaceOperation::Hdf5LinSpaceOperation(Parameters Settings)
    : mpImpl(new Impl)
{
    KRATOS_TRY
    Settings.ValidateAndAssignDefaults(this->GetDefaultParameters());
    mpImpl->mFilePath = Settings["file_path"].Get<std::string>();
    mpImpl->mPrefix = Settings["prefix"].Get<std::string>();
    mpImpl->mBegin = Settings["begin"].Get<int>();
    mpImpl->mStride = Settings["stride"].Get<int>();
    mpImpl->mCount = Settings["count"].Get<int>();
    mpImpl->mOverwrite = Settings["overwrite"].Get<bool>();
    KRATOS_CATCH("")
}


Hdf5LinSpaceOperation::Hdf5LinSpaceOperation(Ref<Model>, Parameters Settings)
    : Hdf5LinSpaceOperation(Settings)
{
}


Hdf5LinSpaceOperation::Hdf5LinSpaceOperation(const Hdf5LinSpaceOperation& rRhs)
    : mpImpl(new Impl(*rRhs.mpImpl))
{
}


Hdf5LinSpaceOperation& Hdf5LinSpaceOperation::operator=(const Hdf5LinSpaceOperation& rRhs)
{
    *mpImpl = *rRhs.mpImpl;
    return *this;
}


Hdf5LinSpaceOperation::~Hdf5LinSpaceOperation()
{
}


void Hdf5LinSpaceOperation::Execute()
{
    KRATOS_TRY

    // Open the input file
    Parameters file_parameters;
    file_parameters.AddString("file_name", mpImpl->mFilePath.string());
    file_parameters.AddString("file_access_mode", "read_write");
    DataCommunicator serial_communicator;
    HDF5::File file(serial_communicator, file_parameters);

    if (file.HasPath(mpImpl->mPrefix) && !mpImpl->mOverwrite) {
        // Nothing to do here
        return;
    }

    // Map IDs to indices
    HDF5::File::Vector<int> buffer(mpImpl->mCount);
    IndexPartition<std::size_t>(buffer.size()).for_each(
        [&buffer, this](const std::size_t Index) mutable {
            buffer[Index] = mpImpl->mBegin + Index * mpImpl->mStride;
        }
    );

    // Write the map to the requested path
    HDF5::WriteInfo write_info;
    file.WriteDataSet(mpImpl->mPrefix, buffer, write_info);

    KRATOS_CATCH("")
}


Parameters Hdf5LinSpaceOperation::GetDefaultParameters() const
{
    return Parameters(R"({
        "file_path" : "",
        "prefix" : "",
        "begin" : 0,
        "stride" : 1,
        "count" : 0,
        "overwrite" : false
    })");
}


} // namespace Kratos
