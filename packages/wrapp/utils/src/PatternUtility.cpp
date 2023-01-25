/// @author Máté Kelemen

// --- Core Includes ---
#include "includes/define.h"
#include "includes/exception.h"

// --- WRApp Includes ---
#include "wrapp/utils/inc/PatternUtility.hpp"

// --- STL Includes ---
#include <algorithm>
#include <iomanip>
#include <sstream>
#include <filesystem>


namespace Kratos {


std::pair<std::string,std::regex> RegexUtility::Integer()
{
    std::pair<std::string,std::regex> output;

    output.first = R"(0|(?:-?[1-9]+[0-9]*))";
    output.second = std::regex(output.first);

    return output;
}


std::pair<std::string,std::regex> RegexUtility::UnsignedInteger()
{
    std::pair<std::string,std::regex> output;

    output.first = R"(0|(?:[1-9]+[0-9]*))";
    output.second = std::regex(output.first);

    return output;
}


std::pair<std::string,std::regex> RegexUtility::FloatingPoint()
{
    std::pair<std::string,std::regex> output;

    // Clutter due to the many uncapturing groups
    output.first = R"(-?(?:(?:(?:[1-9][0-9]*)(?:\.[0-9]*)?)|(?:0(?:\.[0-9]*)?))(?:[eE][\+-]?[0-9]+)?)";
    output.second = std::regex(output.first);

    return output;
}


PlaceholderPattern::PlaceholderPattern(const std::string& rPattern,
                                       const PlaceholderMap& rPlaceholderMap)
    : mPattern(rPattern),
      mPlaceholderGroupMap(),
      mRegexString(FormatRegexLiteral(rPattern)),
      mRegex()
{
    KRATOS_TRY

    using PositionPair = std::pair<std::size_t,PlaceholderMap::const_iterator>;
    const auto number_of_placeholders = rPlaceholderMap.size();

    // Array for tracking position-placeholder pairs for assigning
    // regex groups to placeholders later.
    // {position_in_pattern, it_placeholder_regex_pair}
    std::vector<PositionPair> position_map;
    position_map.reserve(number_of_placeholders);

    // Replace placeholders with their corresponding regex strings
    // and note their positions in the pattern
    PlaceholderMap::const_iterator it_pair = rPlaceholderMap.begin();
    const auto it_end = rPlaceholderMap.end();

    for ( ; it_pair!=it_end; ++it_pair){
        // Make sure that input pattern has no capturing groups of its own.
        KRATOS_ERROR_IF(std::regex(it_pair->second).mark_count())
            << "pattern " << it_pair->second
            << " of placeholder '" << it_pair->first << "'"
            << " has internal capturing group(s) (this is forbidden in PlaceholderPattern)";

        // Wrap the regex in a group
        std::string regex = "(" + it_pair->second + ")";

        const auto placeholder_size = it_pair->first.size();
        const auto regex_size = regex.size();
        const int size_difference = regex_size - placeholder_size;

        while (true) {
            // Find the next instance of the current placeholder
            const auto position_in_pattern = mRegexString.find(it_pair->first);

            // Replace it with its regex (if found)
            if (position_in_pattern != std::string::npos) {
                mRegexString.replace(position_in_pattern, placeholder_size, regex);
            } else {
                break;
            }

            // Update positions
            for (auto& r_pair : position_map) {
                if (position_in_pattern < r_pair.first) r_pair.first += size_difference;
            }

            position_map.emplace_back(position_in_pattern, it_pair);
        } // while placeholder in pattern
    } // for placeholder in rPlaceHolderMap

    // Replace positions with indices in ascending order (based on position)
    // in lieu of std::transform_if
    std::sort(
        position_map.begin(),
        position_map.end(),
        [](const PositionPair& rLeft, const PositionPair& rRight) {return rLeft.first < rRight.first;});

    std::size_t index = 0;
    for (auto& r_pair : position_map) r_pair.first = index++;

    // Populate the placeholder - group index map
    it_pair = rPlaceholderMap.begin();
    for ( ; it_pair!=it_end; ++it_pair) {
        // Move the placeholder string and construct an associated empty index array
        auto emplace_result = mPlaceholderGroupMap.emplace(it_pair->first, PlaceholderGroupMap::mapped_type());

        // Fill the index array with the group indices
        for (const auto& r_pair : position_map) {
            if (r_pair.second == it_pair) emplace_result.first->second.push_back(r_pair.first);
        }
    }

    // Remove placeholders that aren't in the pattern
    auto it_erase = mPlaceholderGroupMap.begin();
    while (it_erase!=mPlaceholderGroupMap.end()) {
        if (it_erase->second.empty()) {
            it_erase = mPlaceholderGroupMap.erase(it_erase);
        } else {
            ++it_erase;
        }
    }

    // Construct the regex
    mRegexString = "^" + mRegexString + "$";
    mRegex = std::regex(mRegexString);

    KRATOS_CATCH("");
} // PlaceholderPattern::PlaceholderPattern


bool PlaceholderPattern::IsAMatch(const std::string& rString) const
{
    KRATOS_TRY

    return std::regex_match(rString, mRegex);

    KRATOS_CATCH("");
} // PlaceholderPattern::IsAMatch


PlaceholderPattern::MatchType PlaceholderPattern::Match(const std::string& rString) const
{
    KRATOS_TRY

    std::smatch results;
    MatchType output;

    // Perform regex search and extract matches
    if (std::regex_match(rString, results, mRegex)) {
        for (auto& r_pair : mPlaceholderGroupMap) {
            // Construct empty group matches
            auto emplace_result = output.emplace(r_pair.first, MatchType::value_type::second_type());

            // Collect matches for the current placeholder
            for (auto i_group : r_pair.second) {
                // First match (index 0) is irrelevant because it's the entire pattern,
                // the rest is offset by 1
                const auto i_group_match = i_group + 1;

                if (!results.str(i_group_match).empty()) {
                    emplace_result.first->second.push_back(results.str(i_group_match));
                }
            } // for i_group
        } // for placeholder, group_indices
    } /*if regex_match*/ else {
        KRATOS_ERROR << "'" << rString << "' is not a match for '" << this->GetRegexString() << "'";
    }

    return output;

    KRATOS_CATCH("");
}


std::string PlaceholderPattern::Apply(const PlaceholderMap& rPlaceholderValueMap) const
{
    KRATOS_TRY

    auto output = mPattern;

    for (const auto& r_pair : rPlaceholderValueMap) {
        KRATOS_ERROR_IF(mPlaceholderGroupMap.find(r_pair.first)==mPlaceholderGroupMap.end()) << r_pair.first << " is not a registered placeholder in " << mPattern;
        while (true) {
            auto position = output.find(r_pair.first);
            if (position != output.npos) {
                output.replace(position, r_pair.first.size(), r_pair.second);
            } else {
                break;
            }
        } // while placeholder in output
    } // for placeholder, value in map

    return output;

    KRATOS_CATCH("");
}


const std::regex& PlaceholderPattern::GetRegex() const
{
    return mRegex;
}


const std::string& PlaceholderPattern::GetRegexString() const
{
    return mRegexString;
}


const std::string& PlaceholderPattern::GetPatternString() const
{
    return mPattern;
}


const ModelPartPattern::PlaceholderMap& ModelPartPattern::GetPlaceholderMap()
{
    if (mModelPartPlaceholderMap.empty()) {
        mModelPartPlaceholderMap = PlaceholderMap {
            {"<model_part_name>", ".+"},
            {"<step>", RegexUtility::UnsignedInteger().first},
            {"<time>", RegexUtility::FloatingPoint().first},
            {"<rank>", RegexUtility::Integer().first}
        };
    }
    return mModelPartPlaceholderMap;
}


std::string PlaceholderPattern::FormatRegexLiteral(const std::string& rLiteral)
{
    KRATOS_TRY

    auto output = rLiteral;

    for (char char_to_escape : R"(!$()*+-?[\]^)") {
        std::size_t position = 0;

        std::string escaped;
        escaped.reserve(2);
        escaped.push_back('\\');
        escaped.push_back(char_to_escape);

        while (true) {
            if (output.size() <= position) break;

            position = output.find(char_to_escape, position);
            if (position == output.npos) {
                break;
            } else {
                // Escape the sensitive character
                if (!position || output[position-1] != '\\') {
                    output.replace(position, 1, escaped);
                    position += 2;
                }
            } // if char_to_escape in output
        } // while True
    } // for char_to_escape

    return output;

    KRATOS_CATCH("");
}


ModelPartPattern::PlaceholderMap ModelPartPattern::mModelPartPlaceholderMap;


ModelPartPattern::ModelPartPattern(const std::string& rPattern)
    : PlaceholderPattern(rPattern, ModelPartPattern::GetPlaceholderMap())
{
}


std::string ModelPartPattern::Apply(const ModelPart& rModelPart) const
{
    KRATOS_TRY

    // TODO: implement formatting, see the documentation in the header. @matekelemen

    ModelPartPattern::PlaceholderMap map;
    const auto& r_pattern = this->GetPatternString();

    if (r_pattern.find("<model_part_name>") != r_pattern.npos) {
        map.emplace("<model_part_name>", rModelPart.Name());
    }

    if (r_pattern.find("<step>") != r_pattern.npos) {
        map.emplace("<step>", std::to_string(rModelPart.GetProcessInfo().GetValue(STEP)));
    }

    if (r_pattern.find("<time>") != r_pattern.npos) {
        // Hardcoded formatting - to be changed later
        std::stringstream stream;
        stream << std::scientific << std::setprecision(4) << rModelPart.GetProcessInfo().GetValue(TIME);
        map.emplace("<time>", stream.str());
    }

    if (r_pattern.find("<rank>") != r_pattern.npos) {
        map.emplace("<rank>", std::to_string(rModelPart.GetCommunicator().MyPID()));
    }

    return this->Apply(map);

    KRATOS_CATCH("");
}


ModelPartPattern::ModelPartPattern(const std::string& rPattern, const PlaceholderMap& rPlaceholderMap)
    : PlaceholderPattern(rPattern, rPlaceholderMap)
{
}


CheckpointPattern::CheckpointPattern(const std::string& rPattern)
    : ModelPartPattern(rPattern, CheckpointPattern::GetPlaceholderMap())
{
}


std::string CheckpointPattern::Apply(const ModelPart& rModelPart, std::size_t PathID) const
{
    KRATOS_TRY

    std::string output = ModelPartPattern::Apply(rModelPart);
    PlaceholderMap map {{"path_id", std::to_string(PathID)}};
    this->Apply(map);
    return output;

    KRATOS_CATCH("")
}


const CheckpointPattern::PlaceholderMap& CheckpointPattern::GetPlaceholderMap()
{
    if (mCheckpointPlaceholderMap.empty()) {
        mCheckpointPlaceholderMap = ModelPartPattern::GetPlaceholderMap();
        mCheckpointPlaceholderMap.emplace("<path_id>", RegexUtility::UnsignedInteger().first);
    }
    return mCheckpointPlaceholderMap;
}


CheckpointPattern::PlaceholderMap CheckpointPattern::mCheckpointPlaceholderMap;


} // namespace Kratos