/// @author Máté Kelemen

// --- WRApp Includes ---
#include "wrapp/utils/inc/Hdf5IdToIndexOperation.hpp" // Hdf5IdToIndexOperation
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


struct Hdf5IdToIndexOperation::Impl
{
    std::filesystem::path mFilePath;

    std::string mInputPrefix;

    std::string mOutputPrefix;

    bool mOverwrite;
}; // Hdf5IdToIndexOperation


Hdf5IdToIndexOperation::Hdf5IdToIndexOperation()
    : mpImpl(new Impl)
{
}


Hdf5IdToIndexOperation::Hdf5IdToIndexOperation(Parameters Settings)
    : mpImpl(new Impl)
{
    KRATOS_TRY
    Settings.ValidateAndAssignDefaults(this->GetDefaultParameters());
    mpImpl->mFilePath = Settings["file_path"].Get<std::string>();
    mpImpl->mInputPrefix = Settings["input_prefix"].Get<std::string>();
    mpImpl->mOutputPrefix = Settings["output_prefix"].Get<std::string>();
    mpImpl->mOverwrite = Settings["overwrite"].Get<bool>();
    KRATOS_CATCH("")
}


Hdf5IdToIndexOperation::Hdf5IdToIndexOperation(Ref<Model>, Parameters Settings)
    : Hdf5IdToIndexOperation(Settings)
{
}


Hdf5IdToIndexOperation::Hdf5IdToIndexOperation(const Hdf5IdToIndexOperation& rRhs)
    : mpImpl(new Impl(*rRhs.mpImpl))
{
}


Hdf5IdToIndexOperation& Hdf5IdToIndexOperation::operator=(const Hdf5IdToIndexOperation& rRhs)
{
    *mpImpl = *rRhs.mpImpl;
    return *this;
}


Hdf5IdToIndexOperation::~Hdf5IdToIndexOperation()
{
}


void Hdf5IdToIndexOperation::Execute()
{
    KRATOS_TRY

    // Open the input file
    Parameters file_parameters;
    file_parameters.AddString("file_name", mpImpl->mFilePath.string());
    file_parameters.AddString("file_access_mode", "read_write");
    DataCommunicator serial_communicator;
    HDF5::File file(serial_communicator, file_parameters);

    // Check for required paths
    KRATOS_ERROR_IF_NOT(file.HasPath(mpImpl->mInputPrefix))
        << mpImpl->mFilePath << ":" << mpImpl->mInputPrefix
        << " does not exist";

    KRATOS_ERROR_IF_NOT(file.IsDataSet(mpImpl->mInputPrefix))
        << mpImpl->mFilePath << ":" << mpImpl->mInputPrefix
        << " is not a dataset";

    KRATOS_ERROR_IF_NOT(file.HasDataType<int>(mpImpl->mInputPrefix))
        << mpImpl->mFilePath << ":" << mpImpl->mInputPrefix
        << " is not an integer array";

    if (file.HasPath(mpImpl->mOutputPrefix)) {
        if (mpImpl->mOverwrite) {
            // @todo @matekelemen
            KRATOS_ERROR
                << "overwriting an existing dataset is not supprted yet.\n"
                << mpImpl->mFilePath << ":" << mpImpl->mOutputPrefix;
        } else {
            // Nothing to do here
            return;
        }
    }

    // Read the input dataset's shape
    const auto shape = file.GetDataDimensions(mpImpl->mInputPrefix);
    KRATOS_ERROR_IF_NOT(shape.size() == 1)
        << mpImpl->mFilePath << ":" << mpImpl->mOutputPrefix
        << " is not a flat array (dimensions: " << shape.size() << ")";

    // Read the input array
    HDF5::File::Vector<int> buffer(shape.front(), 0);
    file.ReadDataSet(mpImpl->mInputPrefix, buffer, 0u, shape.front());

    // Find the highest ID
    // @todo boost ublas vector iterator is not random access??? @matekelemen
    //const auto max_id = block_for_each<MaxReduction<decltype(buffer)::value_type>>(
    //    buffer,
    //    [](const auto Id) {return Id;}
    //);
    const auto max_id = IndexPartition<std::size_t>(buffer.size()).for_each<MaxReduction<int>>(
        [&buffer](std::size_t Index) {return buffer[Index];}
    );

    // Map IDs to indices
    HDF5::File::Vector<int> map(max_id + 1);
    IndexPartition<std::size_t>(buffer.size()).for_each(
        [&buffer, &map](const std::size_t Index) mutable {
            if (Index < buffer.size()) {
                map[buffer[Index]] = Index;
            }
        }
    );

    // Write the map to the requested path
    HDF5::WriteInfo write_info;
    file.WriteDataSet(mpImpl->mOutputPrefix, map, write_info);

    KRATOS_CATCH("")
}


Parameters Hdf5IdToIndexOperation::GetDefaultParameters() const
{
    return Parameters(R"({
        "file_path" : "",
        "input_prefix" : "",
        "output_prefix" : "",
        "overwrite" : false
    })");
}


} // namespace Kratos
