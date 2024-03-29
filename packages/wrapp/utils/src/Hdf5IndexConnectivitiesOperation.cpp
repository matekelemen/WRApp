/// @author Máté Kelemen

// --- HDF5 Includes ---
#include "custom_io/hdf5_file.h" // HDF5::File

// --- WRApp Includes ---
#include "wrapp/utils/inc/Hdf5IndexConnectivitiesOperation.hpp" // Hdf5IndexConnectivitiesOperation

// --- Core Includes ---
#include "includes/data_communicator.h" // DataCommunicator
#include "utilities/parallel_utilities.h" // IndexPartition
#include "utilities/reduction_utilities.h" // MaxReduction

// --- STL Includes ---
#include <filesystem> // filesystem::path
#include <string> // string
#include <unordered_map> // unordered_map



namespace Kratos::WRApp {


namespace {
HDF5::File::Vector<int> MakeIdMap(Ref<const HDF5::File::Vector<int>> rIds)
{
    HDF5::File::Vector<int> output;

    // Find the highest ID and resize the output array accordingly
    const std::size_t max_id = IndexPartition<std::size_t>(rIds.size()).for_each<MaxReduction<int>>(
        [&rIds](std::size_t Index){return rIds[Index];}
    );
    output.resize(max_id + 1, false); // <== kratos IDs are 1-based

    // Build the ID-index map
    IndexPartition<std::size_t>(output.size()).for_each([&rIds, &output](std::size_t Index) mutable {
        if (Index < rIds.size()) {
            output[rIds[Index]] = Index;
        }
    });

    return output;
}

void WriteSubGroupMaps(Ref<HDF5::File> rFile,
                       Ref<const std::string> rInputSubGroupPrefix,
                       Ref<const std::string> rOutputSubGroupPrefix,
                       Ref<const HDF5::File::Vector<int>> rNodeIdMap,
                       Ref<const std::unordered_map<std::string,HDF5::File::Vector<int>>> rCellIdMaps)
{
    KRATOS_TRY
    const auto subgroup_names = rFile.GetGroupNames(rInputSubGroupPrefix);
    for (Ref<const std::string> r_subgroup_name : subgroup_names) {
        const std::string input_subgroup_prefix = rInputSubGroupPrefix + "/" + r_subgroup_name;
        const std::string output_subgroup_prefix = rOutputSubGroupPrefix + "/" + r_subgroup_name;

        // Write node set
        {
            HDF5::File::Vector<int> node_ids;

            KRATOS_TRY
                const std::string input_node_id_prefix = input_subgroup_prefix + "/" + "NodeIds";

                // Read node IDs
                const auto node_id_shape = rFile.GetDataDimensions(input_node_id_prefix);
                KRATOS_ERROR_IF(node_id_shape.empty());
                const std::size_t node_count = node_id_shape[0];
                node_ids.resize(node_count, false);
                rFile.ReadDataSet(input_node_id_prefix, node_ids, 0, node_ids.size());
            KRATOS_CATCH("")

            // Map node IDs to indices
            IndexPartition<std::size_t>(node_ids.size()).for_each([&rNodeIdMap, &node_ids](std::size_t Index) mutable {
                node_ids[Index] = rNodeIdMap[node_ids[Index]];
            });

            // Write node indices
            KRATOS_TRY
                const std::string output_node_index_prefix = output_subgroup_prefix + "/Nodes/Indices";
                [[maybe_unused]] HDF5::WriteInfo write_info;
                rFile.WriteDataSet(output_node_index_prefix,
                                   node_ids,
                                   write_info);
            KRATOS_CATCH("")
        }

        // Write cell sets
        for (std::string group_name : {"Elements", "Conditions"}) {
            const std::string input_parent_prefix = input_subgroup_prefix + "/" + group_name;
            KRATOS_WATCH(input_parent_prefix);

            if (rFile.HasPath(input_parent_prefix)) {
                const std::string output_parent_prefix = output_subgroup_prefix + "/" + group_name;
                KRATOS_WATCH(output_parent_prefix);
                const auto cell_names = rFile.GetGroupNames(input_parent_prefix);
                for (const std::string& r_cell_name : cell_names) {
                    const auto it_cell_id_map = rCellIdMaps.find(r_cell_name);
                    KRATOS_ERROR_IF(it_cell_id_map == rCellIdMaps.end())
                        << "cell type " << r_cell_name << " in subgroup is not in the root set";

                    HDF5::File::Vector<int> cell_ids;

                    // Read cell IDs
                    KRATOS_TRY
                        const std::string cell_id_prefix = input_parent_prefix + "/" + r_cell_name + "/Ids";
                        const auto cell_id_shape = rFile.GetDataDimensions(cell_id_prefix);
                        KRATOS_ERROR_IF(cell_id_shape.empty());
                        const std::size_t cell_count = cell_id_shape[0];
                        cell_ids.resize(cell_count, false);
                        rFile.ReadDataSet(cell_id_prefix, cell_ids, 0, cell_ids.size());
                    KRATOS_CATCH("")

                    // Map cell IDs to indices
                    IndexPartition<std::size_t>(cell_ids.size()).for_each([&rNodeIdMap, &cell_ids](std::size_t Index) mutable {
                        cell_ids[Index] = rNodeIdMap[cell_ids[Index]];
                    });

                    // Write cell indices to the HDF5 file
                    KRATOS_TRY
                        const std::string output_cell_index_prefix = output_parent_prefix + "/" + r_cell_name + "/Indices";
                        [[maybe_unused]] HDF5::WriteInfo write_info;
                        std::cout << "writing cell set to " << output_cell_index_prefix << "\n";
                        rFile.WriteDataSet(output_cell_index_prefix,
                                           cell_ids,
                                           write_info);
                    KRATOS_CATCH("")
                } // for r_cell_name in cell_names
            } // if input_parent_prefix in rFile
        } // for group_name in ("Elements", "Conditions")
    } // for r_subgroup_names in subgroup_names

        // Recursive call to nested subgroups
        const std::string input_nesting_prefix = input_subgroup_prefix + "/SubModelParts";
        if (rFile.HasPath(input_nesting_prefix)) {
            KRATOS_TRY
            const std::string output_nesting_prefix = output_subgroup_prefix + "/SubModelParts";
            WriteSubGroupMaps(rFile,
                              input_nesting_prefix,
                              output_nesting_prefix,
                              rNodeIdMap,
                              rCellIdMaps);
            KRATOS_CATCH(input_nesting_prefix)
        }
    } // for r_subgroup_names in subgroup_names
    KRATOS_CATCH("")
}
} // Anonymous namespace


struct Hdf5IndexConnectivitiesOperation::Impl
{
    std::filesystem::path mFilePath;

    std::string mInputPrefix;

    std::string mOutputPrefix;

    bool mOverwrite;
}; // struct Hdf5IndexConnectivitiesOperation::Impl


Hdf5IndexConnectivitiesOperation::Hdf5IndexConnectivitiesOperation()
    : mpImpl(new Impl)
{
}


Hdf5IndexConnectivitiesOperation::Hdf5IndexConnectivitiesOperation(Parameters Settings)
    : Hdf5IndexConnectivitiesOperation()
{
    KRATOS_TRY
    Settings.ValidateAndAssignDefaults(this->GetDefaultParameters());
    mpImpl->mFilePath = Settings["file_path"].Get<std::string>();
    mpImpl->mInputPrefix = Settings["input_prefix"].Get<std::string>();
    mpImpl->mOutputPrefix = Settings["output_prefix"].Get<std::string>();
    mpImpl->mOverwrite = Settings["overwrite"].Get<bool>();

    // Remove trailing forward slashes / from prefixes
    for (Ptr<std::string> p_prefix : {&mpImpl->mInputPrefix, &mpImpl->mOutputPrefix}) {
        if (1 < p_prefix->size() && p_prefix->back() == '/') {
            p_prefix->resize(p_prefix->size() - 1);
        }
    }
    KRATOS_CATCH("")
}


Hdf5IndexConnectivitiesOperation::Hdf5IndexConnectivitiesOperation(Ref<Model> rModel, Parameters Settings)
    : Hdf5IndexConnectivitiesOperation(Settings)
{
}


Hdf5IndexConnectivitiesOperation::Hdf5IndexConnectivitiesOperation(const Hdf5IndexConnectivitiesOperation& rRhs)
    : mpImpl(new Impl(*rRhs.mpImpl))
{
}


Hdf5IndexConnectivitiesOperation& Hdf5IndexConnectivitiesOperation::operator=(const Hdf5IndexConnectivitiesOperation& rRhs)
{
    *mpImpl = *rRhs.mpImpl;
    return *this;
}


Hdf5IndexConnectivitiesOperation::~Hdf5IndexConnectivitiesOperation()
{
}


void Hdf5IndexConnectivitiesOperation::Execute()
{
    KRATOS_TRY

    // Open the input file
    std::unique_ptr<HDF5::File> p_file;
    DataCommunicator serial_communicator;

    {
        Parameters file_parameters;
        file_parameters.AddString("file_name", mpImpl->mFilePath.string());
        file_parameters.AddString("file_access_mode", "read_write");
        p_file = std::make_unique<HDF5::File>(serial_communicator, file_parameters);
    }

    // Check required paths
    KRATOS_ERROR_IF_NOT(p_file->HasPath(mpImpl->mInputPrefix))
        << mpImpl->mFilePath << ":" << mpImpl->mInputPrefix << " does not exist";

    if (p_file->HasPath(mpImpl->mOutputPrefix)) {
        if (mpImpl->mOverwrite) {
            KRATOS_ERROR << "overwriting an existing HDF5 group is not supported yet\n"
                         << mpImpl->mFilePath << ":" << mpImpl->mOutputPrefix;
        } else {
            // Nothing to do here
            return;
        }
    }

    // Build and write the node ID map
    HDF5::File::Vector<int> node_id_map;
    {
        KRATOS_TRY
        const std::string input_node_id_prefix = mpImpl->mInputPrefix + "/Nodes/Local/Ids";
        const std::string output_node_id_prefix = mpImpl->mOutputPrefix + "/Nodes/IdMap";

        const auto node_id_shape = p_file->GetDataDimensions(input_node_id_prefix);
        KRATOS_ERROR_IF(node_id_shape.empty());
        const std::size_t node_count = node_id_shape[0];
        HDF5::File::Vector<int> node_ids(node_count);
        p_file->ReadDataSet(input_node_id_prefix, node_ids, 0, node_ids.size());
        node_id_map = MakeIdMap(node_ids);

        [[maybe_unused]] HDF5::WriteInfo write_info;
        p_file->WriteDataSet(output_node_id_prefix, node_id_map, write_info);
        KRATOS_CATCH("nodes")
    }

    // Build and write the element and condition maps
    std::unordered_map<
        std::string,
        HDF5::File::Vector<int>
    > cell_id_maps;

    for (std::string parent_group_name : {"Elements", "Conditions"}) {
        const std::string input_group_prefix = mpImpl->mInputPrefix + "/" + parent_group_name;
        const std::string output_group_prefix = mpImpl->mOutputPrefix + "/" + parent_group_name;
        const auto group_names = p_file->GetGroupNames(input_group_prefix);

        for (const std::string& r_cell_group_name : group_names) {
            const auto emplace_result = cell_id_maps.emplace(r_cell_group_name, HDF5::File::Vector<int> {});
            KRATOS_ERROR_IF_NOT(emplace_result.second) << "duplicate cell type: " << r_cell_group_name;
            Ref<HDF5::File::Vector<int>> r_cell_map = emplace_result.first->second;

            KRATOS_TRY
                const std::string input_cell_id_prefix = input_group_prefix + "/" + r_cell_group_name + "/Ids";
                const std::string output_cell_id_prefix = output_group_prefix + "/" + r_cell_group_name + "/IdMap";

                const auto cell_id_shape = p_file->GetDataDimensions(input_cell_id_prefix);
                KRATOS_ERROR_IF(cell_id_shape.empty());
                const std::size_t cell_count = cell_id_shape[0];
                HDF5::File::Vector<int> cell_ids(cell_count);
                p_file->ReadDataSet(input_cell_id_prefix, cell_ids, 0, cell_ids.size());

                r_cell_map = MakeIdMap(cell_ids);
                [[maybe_unused]] HDF5::WriteInfo write_info;
                p_file->WriteDataSet(output_cell_id_prefix, r_cell_map, write_info);
            KRATOS_CATCH(r_cell_group_name)

            HDF5::File::Matrix<int> index_connectivities;

            // Read ID-based connectivities
            KRATOS_TRY
                const std::string input_cell_connectivity_prefix = input_group_prefix + "/" + r_cell_group_name + "/Connectivities";
                HDF5::File::Matrix<int> id_connectivities;

                const auto connectivity_shape = p_file->GetDataDimensions(input_cell_connectivity_prefix);
                KRATOS_ERROR_IF(connectivity_shape.empty());
                p_file->ReadDataSet(input_cell_connectivity_prefix, id_connectivities, 0, connectivity_shape[0]);

                // Map ID-based connectivities to index-based ones
                index_connectivities.resize(id_connectivities.size1(), id_connectivities.size2());
                IndexPartition<std::size_t>(index_connectivities.size1()).for_each(
                    [&index_connectivities, &id_connectivities, &node_id_map](std::size_t iRow) mutable {
                        for (std::size_t i_column=0ul; i_column<id_connectivities.size2(); ++i_column) {
                            index_connectivities(iRow, i_column) = node_id_map[id_connectivities(iRow, i_column)];
                        } // for i_column
                    } // lambda
                ); // IndexPartition
            KRATOS_CATCH("")

            // Write index-based connectivities to the HDF5 file
            KRATOS_TRY
                const std::string output_cell_connectivity_prefix = output_group_prefix + "/" + r_cell_group_name + "/Connectivities";
                [[maybe_unused]] HDF5::WriteInfo write_info;
                p_file->WriteDataSet(output_cell_connectivity_prefix,
                                     index_connectivities,
                                     write_info);
            KRATOS_CATCH("")
        } // for r_cell_group_name in group_names
    } // for parent_group_name in ("Elements", "Conditions")

    // Parse subgroups
    const std::string input_nesting_prefix = mpImpl->mInputPrefix + "/SubModelParts";
    if (p_file->HasPath(input_nesting_prefix)) {
        KRATOS_TRY
        const std::string output_nesting_prefix = mpImpl->mOutputPrefix + "/SubModelParts";
        WriteSubGroupMaps(*p_file,
                          input_nesting_prefix,
                          output_nesting_prefix,
                          node_id_map,
                          cell_id_maps);
        KRATOS_CATCH("")
    }

    KRATOS_CATCH("")
}


Parameters Hdf5IndexConnectivitiesOperation::GetDefaultParameters() const
{
    return Parameters(R"({
        "file_path" : "",
        "input_prefix" : "",
        "output_prefix" : "",
        "overwrite" : false
    })");
}


} // namespace Kratos::WRApp
