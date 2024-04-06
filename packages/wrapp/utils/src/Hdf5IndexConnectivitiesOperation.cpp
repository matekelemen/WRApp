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
#include <algorithm> // sort
#include <numeric> // iota



namespace Kratos::WRApp {


namespace {
void FillIdMap(Ref<const HDF5::File::Vector<int>> rIds,
               Ref<HDF5::File::Vector<int>> rMap)
{
    // Build the ID-index map
    IndexPartition<std::size_t>(rMap.size()).for_each([&rIds, &rMap](std::size_t Index) {
        if (Index < rIds.size()) {
            KRATOS_ERROR_IF_NOT(static_cast<std::size_t>(rIds[Index]) < rMap.size()); // <== prevent segfaults
            rMap[rIds[Index]] = Index;
        }
    });
}

void WriteSubGroupMaps(Ref<HDF5::File> rFile,
                       Ref<const std::string> rInputSubGroupPrefix,
                       Ref<const std::string> rOutputSubGroupPrefix,
                       Ref<const HDF5::File::Vector<int>> rNodeIdMap,
                       Ref<const HDF5::File::Vector<int>> rElementIdMap,
                       Ref<const HDF5::File::Vector<int>> rConditionIdMap)
{
    KRATOS_TRY
    const auto subgroup_names = rFile.GetGroupNames(rInputSubGroupPrefix);
    for (Ref<const std::string> r_subgroup_name : subgroup_names) {
        if (r_subgroup_name == "Elements" || r_subgroup_name == "Conditions" || r_subgroup_name == "Properties") continue;

        const std::string input_subgroup_prefix = rInputSubGroupPrefix + "/" + r_subgroup_name;
        const std::string output_subgroup_prefix = rOutputSubGroupPrefix + "/" + r_subgroup_name;

        // Write node set
        {
            HDF5::File::Vector<int> node_ids;

            // Read node IDs
            KRATOS_TRY
                const std::string input_node_id_prefix = input_subgroup_prefix + "/" + "NodeIds";
                const auto node_id_shape = rFile.GetDataDimensions(input_node_id_prefix);
                KRATOS_ERROR_IF(node_id_shape.empty());
                const std::size_t node_count = node_id_shape[0];
                node_ids.resize(node_count, false);
                rFile.ReadDataSet(input_node_id_prefix, node_ids, 0, node_ids.size());
            KRATOS_CATCH("")

            // Map IDs to indices
            IndexPartition<std::size_t>(node_ids.size()).for_each([&node_ids, &rNodeIdMap](std::size_t iNode){
                node_ids[iNode] = rNodeIdMap[node_ids[iNode]];
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
        for (auto [group_name, p_id_map] : std::array<std::pair<std::string,Ptr<const HDF5::File::Vector<int>>>,2> {{{"Elements", &rElementIdMap}, {"Conditions", &rConditionIdMap}}}) {
            const std::string input_parent_prefix = input_subgroup_prefix + "/" + group_name;
            Ref<const HDF5::File::Vector<int>> r_id_map = *p_id_map;

            if (rFile.HasPath(input_parent_prefix)) {
                const std::string output_parent_prefix = output_subgroup_prefix + "/" + group_name;
                const auto cell_names = rFile.GetGroupNames(input_parent_prefix);
                for (const std::string& r_cell_name : cell_names) {
                    // Read cell IDs
                    HDF5::File::Vector<int> cell_ids;
                    HDF5::File::Vector<int> cell_indices;
                    KRATOS_TRY
                        const std::string cell_id_prefix = input_parent_prefix + "/" + r_cell_name + "/Ids";
                        const auto cell_id_shape = rFile.GetDataDimensions(cell_id_prefix);
                        KRATOS_ERROR_IF(cell_id_shape.empty());
                        const std::size_t cell_count = cell_id_shape[0];
                        cell_ids.resize(cell_count, false);
                        rFile.ReadDataSet(cell_id_prefix, cell_ids, 0, cell_ids.size());
                    KRATOS_CATCH("")

                    // Map cell IDs to indices
                    cell_indices.resize(cell_ids.size(), false);
                    IndexPartition<std::size_t>(cell_ids.size()).for_each([&cell_ids, &cell_indices, &r_id_map](std::size_t iCell) {
                        cell_indices[iCell] = r_id_map[cell_ids[iCell]];
                    });

                    // Write cell indices to the HDF5 file
                    KRATOS_TRY
                        const std::string output_cell_index_prefix = output_parent_prefix + "/" + r_cell_name + "/TypeIndices";
                        [[maybe_unused]] HDF5::WriteInfo write_info;
                        rFile.WriteDataSet(output_cell_index_prefix,
                                           cell_indices,
                                           write_info);
                    KRATOS_CATCH("")
                } // for r_cell_name in cell_names

            } // if r_subgroup_name in subgroup_names
        } // for group_name in ("Elements", "Conditions")

        KRATOS_TRY
            WriteSubGroupMaps(rFile,
                              input_subgroup_prefix,
                              output_subgroup_prefix + "/SubModelParts",
                              rNodeIdMap,
                              rElementIdMap,
                              rConditionIdMap);
        KRATOS_CATCH(input_subgroup_prefix)
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

    if (p_file->HasPath(mpImpl->mOutputPrefix) && !mpImpl->mOverwrite) {
        // Nothing to do here
        return;
    }

    // Build and write the node ID map
    HDF5::File::Vector<int> node_id_map;
    {
        KRATOS_TRY
        const std::string input_node_id_prefix = mpImpl->mInputPrefix + "/Nodes/Local/Ids";

        KRATOS_ERROR_IF_NOT(p_file->HasPath(input_node_id_prefix));
        const auto node_id_shape = p_file->GetDataDimensions(input_node_id_prefix);
        KRATOS_ERROR_IF(node_id_shape.empty());
        const std::size_t node_count = node_id_shape[0];
        HDF5::File::Vector<int> node_ids(node_count);
        p_file->ReadDataSet(input_node_id_prefix, node_ids, 0, node_ids.size());

        // Find the highest ID and resize the output array accordingly
        const std::size_t max_id = IndexPartition<std::size_t>(node_ids.size()).for_each<MaxReduction<int>>(
            [&node_ids](std::size_t Index){return node_ids[Index];}
        );
        std::sort(node_ids.begin(), node_ids.end());
        node_id_map.resize(max_id + 1, false); // <== kratos IDs are 1-based

        // Map IDs to indices
        FillIdMap(node_ids, node_id_map);

        // Generate an index set for nodes
        // This is necessary to display the default topology, which is a point cloud.
        std::iota(node_ids.begin(), node_ids.end(), 0);
        KRATOS_TRY
            const std::string output_node_index_prefix = mpImpl->mOutputPrefix + "/Nodes/Indices";
            [[maybe_unused]] HDF5::WriteInfo write_info;
            p_file->WriteDataSet(output_node_index_prefix, node_ids, write_info);
        KRATOS_CATCH("")
        KRATOS_CATCH("")
    }

    // Build the element and condition maps
    // - The basic ID maps relate each cell's ID to its index
    //   within the container that holds ALL cells (necessary for attributes).
    // - The type ID maps relate each cell's ID to its index
    //   within the container that holds all cells of ITS SPECIFIC TYPE (necessary for the mesh).
    HDF5::File::Vector<int> element_type_id_map, condition_type_id_map;

    for (auto [parent_group_name, p_type_id_map] : std::array<std::tuple<std::string,Ptr<HDF5::File::Vector<int>>>,2>
                                                   {{{"Elements",   &element_type_id_map},
                                                     {"Conditions", &condition_type_id_map}}}) {
        const std::string input_group_prefix = mpImpl->mInputPrefix + "/" + parent_group_name;
        const std::string output_group_prefix = mpImpl->mOutputPrefix + "/" + parent_group_name;

        KRATOS_ERROR_IF_NOT(p_file->HasPath(input_group_prefix));
        const auto group_names = p_file->GetGroupNames(input_group_prefix);
        HDF5::File::Vector<int> id_map;
        auto& r_type_id_map = *p_type_id_map; // <== this map will be capured in a lambda later, but capturing structured bindings is a C++20 feature

        // First, collect all cell ids and resize the map accordingly.
        // The assumption here is that each cell is appears exactly once in each
        // group (every element has **one** unique type).
        {
            HDF5::File::Vector<int> all_cell_ids;
            for (const std::string& r_cell_group_name : group_names) {
                KRATOS_TRY
                    const std::string input_cell_id_prefix = input_group_prefix + "/" + r_cell_group_name + "/Ids";
                    KRATOS_ERROR_IF_NOT(p_file->HasPath(input_cell_id_prefix));
                    KRATOS_ERROR_IF_NOT(p_file->IsDataSet(input_cell_id_prefix));
                    const auto cell_id_shape = p_file->GetDataDimensions(input_cell_id_prefix);
                    KRATOS_ERROR_IF(cell_id_shape.empty());
                    HDF5::File::Vector<int> cell_ids;
                    p_file->ReadDataSet(input_cell_id_prefix, cell_ids, 0, cell_id_shape.front());

                    // Concatenate the IDs
                    std::size_t old_size = all_cell_ids.size();
                    all_cell_ids.resize(old_size + cell_ids.size(), true);
                    std::copy(cell_ids.begin(),
                              cell_ids.end(),
                              all_cell_ids.begin() + old_size);
                KRATOS_CATCH(r_cell_group_name)
            }


            // Construct the ID map and write the IDs to file
            // @todo the sorting will have to be done for each MPI range separately @matekelemen
            std::sort(all_cell_ids.begin(), all_cell_ids.end());
            const std::size_t max_cell_id = all_cell_ids.empty() ? 0 : all_cell_ids[all_cell_ids.size() - 1];
            id_map.resize(max_cell_id + 1, false); // <== kratos IDs are 1-based
            r_type_id_map.resize(max_cell_id + 1, false);
            FillIdMap(all_cell_ids, id_map);

            // Write Ids
            KRATOS_TRY
                const std::string output_cell_id_prefix = output_group_prefix + "/Ids";
                [[maybe_unused]] HDF5::WriteInfo write_info;
                p_file->WriteDataSet(output_cell_id_prefix, all_cell_ids, write_info);
            KRATOS_CATCH("")
        } // destroy "all_cell_ids"

        for (const std::string& r_cell_group_name : group_names) {
            const std::string input_cell_group_prefix = input_group_prefix + "/" + r_cell_group_name;
            const std::string output_cell_group_prefix = output_group_prefix + "/" + r_cell_group_name;

            // Write indices
            {
                HDF5::File::Vector<int> cell_ids;

                // Read Ids
                KRATOS_TRY
                    const std::string input_cell_id_prefix = input_cell_group_prefix + "/Ids";
                    KRATOS_ERROR_IF_NOT(p_file->HasPath(input_cell_id_prefix));
                    const auto cell_id_shape = p_file->GetDataDimensions(input_cell_id_prefix);
                    KRATOS_ERROR_IF(cell_id_shape.empty());
                    p_file->ReadDataSet(input_cell_id_prefix, cell_ids, 0, cell_id_shape.front());
                KRATOS_CATCH("")

                // Map cell IDs to type-restricted indices
                std::size_t i_cell = 0ul;
                for (auto id_cell : cell_ids) {
                    r_type_id_map[id_cell] = i_cell++;
                }

                // Write indices
                KRATOS_TRY
                    // Map cell IDs to indices
                    IndexPartition<std::size_t>(cell_ids.size()).for_each([&cell_ids, &id_map](std::size_t iCell){
                        cell_ids[iCell] = id_map[cell_ids[iCell]];
                    });

                    // Write to file
                    const std::string output_cell_index_path = output_cell_group_prefix + "/Indices";
                    [[maybe_unused]] HDF5::WriteInfo write_info;
                    p_file->WriteDataSet(output_cell_index_path, cell_ids, write_info);
                KRATOS_CATCH("")
            } // destroy "cell_ids"

            HDF5::File::Matrix<int> index_connectivities;

            KRATOS_TRY
                // Read ID-based connectivities
                const std::string input_cell_connectivity_prefix = input_cell_group_prefix + "/Connectivities";
                HDF5::File::Matrix<int> id_connectivities;

                KRATOS_ERROR_IF_NOT(p_file->HasPath(input_cell_connectivity_prefix));
                const auto connectivity_shape = p_file->GetDataDimensions(input_cell_connectivity_prefix);
                KRATOS_ERROR_IF(connectivity_shape.empty());
                p_file->ReadDataSet(input_cell_connectivity_prefix, id_connectivities, 0, connectivity_shape.front());

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
                          element_type_id_map,
                          condition_type_id_map);
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
