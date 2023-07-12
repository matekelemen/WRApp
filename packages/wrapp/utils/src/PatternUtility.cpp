/// @author Máté Kelemen

// --- Core Includes ---
#include "includes/define.h"
#include "includes/exception.h"

// --- WRApp Includes ---
#include "wrapp/utils/inc/PatternUtility.hpp"
#include "wr_application/WRApplication_variables.hpp"

// --- STL Includes ---
#include <algorithm>
#include <iomanip>
#include <sstream>
#include <filesystem>
#include <algorithm>


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


PlaceholderPattern::PlaceholderPattern(Ref<const std::string> rPattern,
                                       Ref<const PlaceholderMap> rPlaceholderMap)
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
    for (auto it_pair=rPlaceholderMap.begin() ; it_pair!=it_end; ++it_pair) {
        // Move the placeholder string and construct an associated empty index array
        auto emplace_result = mPlaceholderGroupMap.emplace(it_pair->first, PlaceholderGroupMap::mapped_type(
            PlaceholderGroupMap::mapped_type::value_type()
        ));

        // Fill the index array with the group indices
        for (const auto& r_pair : position_map) {
            if (r_pair.second == it_pair) emplace_result.first->second.value().push_back(r_pair.first);
        }
    }

    // Disable placeholders that aren't in the pattern
    for (auto& r_pair : mPlaceholderGroupMap) {
        if (r_pair.second.value().empty()) {
            r_pair.second = PlaceholderGroupMap::mapped_type();
        } // if placeholder was not found in the pattern
    } // for key, value in mPlaceholderGroupMap

    // Construct the regex
    mRegexString = "^" + mRegexString + "$";
    mRegex = std::regex(mRegexString);

    KRATOS_CATCH("")
    KRATOS_TRY

    // Make sure that PlaceholderPattern::GetPlaceholderMap can
    // handle the input. In particular, it doesn't support patterns
    // in which a placeholder's regex contains the literal that it
    // is followed by. For example, mRegexString:
    // ^firstliteral_(regex_containing_secondliteral)_secondliteral$
    //                                 ^^^^^^^^^^^^^
    //                                 | regex contains literal it is followed by
    const auto reconstructed_map = this->GetPlaceholderMap();
    for (const auto& r_reference_pair : rPlaceholderMap) {
        if (mPlaceholderGroupMap[r_reference_pair.first].has_value()) {              // <== placeholder is present in the pattern
            const std::string reference_regex = "(" + r_reference_pair.second + ")"; // <== account for the extra capturing group
            const auto it_reconstructed = reconstructed_map.find(r_reference_pair.first);
            KRATOS_ERROR_IF(it_reconstructed == reconstructed_map.end());
            KRATOS_ERROR_IF_NOT(reference_regex == it_reconstructed->second)
                << "Reconstructed regex mismatch for placeholder '" << r_reference_pair.first
                << "' in pattern '" << mPattern << "':\n'" << it_reconstructed->second << "' != '" << reference_regex << "'";
        }
    }

    KRATOS_CATCH("")
} // PlaceholderPattern::PlaceholderPattern


bool PlaceholderPattern::IsAMatch(Ref<const std::string> rString) const
{
    KRATOS_TRY

    return std::regex_match(rString, mRegex);

    KRATOS_CATCH("");
} // PlaceholderPattern::IsAMatch


PlaceholderPattern::MatchType PlaceholderPattern::Match(Ref<const std::string> rString) const
{
    KRATOS_TRY

    std::smatch results;
    MatchType output;

    // Perform regex search and extract matches
    if (std::regex_match(rString, results, mRegex)) {
        for (auto& r_pair : mPlaceholderGroupMap) {
            if (r_pair.second.has_value()) {
                // Construct empty group matches
                auto emplace_result = output.emplace(r_pair.first, MatchType::value_type::second_type());

                // Collect matches for the current placeholder
                for (auto i_group : r_pair.second.value()) {
                    // First match (index 0) is irrelevant because it's the entire pattern,
                    // the rest is offset by 1
                    const auto i_group_match = i_group + 1;

                    if (!results.str(i_group_match).empty()) {
                        emplace_result.first->second.push_back(results.str(i_group_match));
                    }
                } // for i_group
            } // for placeholder, group_indices
        } // if group_indices is not None
    } /*if regex_match*/ else {
        KRATOS_ERROR << "'" << rString << "' is not a match for '" << this->GetRegexString() << "'";
    }

    return output;

    KRATOS_CATCH("");
}


std::string PlaceholderPattern::Apply(Ref<const PlaceholderMap> rPlaceholderValueMap) const
{
    KRATOS_TRY

    auto output = mPattern;
    const auto it_group_map_end = mPlaceholderGroupMap.end();

    for (const auto& r_pair : rPlaceholderValueMap) {
        auto it_pair = mPlaceholderGroupMap.find(r_pair.first);
        if (it_pair != it_group_map_end) {
            if (it_pair->second.has_value()) {
                while (true) {
                    auto position = output.find(r_pair.first);
                    if (position != output.npos) {
                        output.replace(position, r_pair.first.size(), r_pair.second);
                    } else {
                        break;
                    }
                } // while placeholder in output
            } // if placeholder in pattern
        } else {
            KRATOS_ERROR << r_pair.first << " is not a registered placeholder in " << mPattern;
        } // unrecognized placeholder
    } // for placeholder, value in map

    return output;

    KRATOS_CATCH("");
}


bool PlaceholderPattern::IsConst() const
{
    return std::none_of(mPlaceholderGroupMap.begin(),
                        mPlaceholderGroupMap.end(),
                        [](const auto& rPair) {
                            return rPair.second.has_value();
                        });
}


Ref<const std::regex> PlaceholderPattern::GetRegex() const
{
    return mRegex;
}


Ref<const std::string> PlaceholderPattern::GetRegexString() const
{
    return mRegexString;
}


PlaceholderPattern::PlaceholderMap PlaceholderPattern::GetPlaceholderMap() const
{
    PlaceholderPattern::PlaceholderMap output;

    // Collect placeholders and their positions within the regex
    // in the order they appear in the input pattern.
    std::vector<std::pair<
        std::size_t,                // <== group index
        Ptr<const std::string>      // <== placeholder
    >> placeholders;

    for (const auto& r_pair : mPlaceholderGroupMap) {
        if (r_pair.second.has_value()) {
            const auto& r_indices = r_pair.second.value();
            std::transform(r_indices.begin(),
                           r_indices.end(),
                           std::back_inserter(placeholders),
                           [&r_pair](std::size_t position){
                                return std::make_pair(position, &r_pair.first);
                           });
        }
    }

    std::sort(placeholders.begin(),
              placeholders.end(),
              [](const auto& r_left, const auto& r_right) {
                return r_left.first < r_right.first;
              });

    // Loop through placeholders in the regex and find their counterparts
    // in the input pattern. Then find the placeholder's end in the pattern,
    // and find the leftovers in the regex, which should yield just enough
    // info to get its representation.
    std::size_t i_pattern = 0;                                              // <== current position within mPattern
    std::size_t i_regex = 0;                                                // <== current position within mRegexString
    std::string literal;                                                    // <== local var for literals between placeholders
    const std::string regex = mRegexString.substr(1,mRegexString.size()-2); // <== strip line begin and end constraints
    for (auto it_pair=placeholders.begin(); it_pair!=placeholders.end(); ++it_pair) {
        const auto& r_placeholder = *it_pair->second;
        const std::size_t i_next = mPattern.find(r_placeholder, i_pattern); // <== find the index of the next placeholder
        KRATOS_ERROR_IF(i_next == mPattern.npos);
        literal = mPattern.substr(i_pattern, i_next - i_pattern);
        i_pattern = i_next + r_placeholder.size(); // <== jump past the placeholder

        // Find the starting pos of the regex based on the literal
        i_regex = regex.find(literal, i_regex);
        KRATOS_ERROR_IF(i_regex == regex.npos)
            << "Cannot find literal '" << literal << "' in regex '"
            << regex << "' while processing placeholder '" << r_placeholder << "'";
        i_regex += literal.size(); // <== jump over the literal

        // Find the literals between the current and next placeholders
        const std::size_t i_literal_end = (it_pair + 1) == placeholders.end() ? mPattern.size() : mPattern.find(*(it_pair + 1)->second, i_pattern);
        KRATOS_ERROR_IF_NOT(i_pattern <= i_literal_end)
            << "Cannot find next placeholder '" << (*(it_pair + 1)->second)
            << "' in pattern " << mPattern;
        literal = mPattern.substr(i_pattern, i_literal_end - i_pattern);
        i_pattern = i_literal_end;

        // The regex corresponding to the current placeholder is the substring in
        // the full regex between the current position and the begin of the literal
        // defined above.
        const std::size_t i_regex_end = literal.empty() ? regex.size() : regex.find(literal, i_regex);
        KRATOS_ERROR_IF(i_regex_end == regex.npos);
        const std::string placeholder_regex = regex.substr(i_regex, i_regex_end - i_regex);
        i_regex = i_regex_end + literal.size(); // <== jump past the regex and the literal

        // Placeholders may occur repeatedly in the pattern, but their regexes must
        // remain identical in each case. Check whether that's true.
        const auto emplace_result = output.emplace(r_placeholder, placeholder_regex);
        if (!emplace_result.second) {
            // If the literal is also part of the placeholder's regex, this will fail.
            // I can't think of a good fix for this right now.
            /// @todo fixme.
            KRATOS_ERROR_IF_NOT(emplace_result.first->second == placeholder_regex)
                << "Placeholder '" << r_placeholder << "' in pattern '" << mPattern
                << "' is associated with different regexes: '" << emplace_result.first->second
                << "' and '" << placeholder_regex << "'. This is an internal error.";
        }
    }
    return output;
}


Ref<const std::string> PlaceholderPattern::GetPatternString() const
{
    return mPattern;
}


ModelPartPattern::PlaceholderMap ModelPartPattern::GetPlaceholderMap()
{
    return PlaceholderMap {
        {"<model_part_name>", ".+"},
        {"<step>", RegexUtility::UnsignedInteger().first},
        {"<time>", RegexUtility::FloatingPoint().first},
        {"<rank>", RegexUtility::Integer().first}
    };
}


std::string PlaceholderPattern::FormatRegexLiteral(const std::string& rLiteral)
{
    KRATOS_TRY

    auto output = rLiteral;

    for (char char_to_escape : R"(!$()*+?[\]^)") {
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


ModelPartPattern::ModelPartPattern(const std::string& rPattern)
    : PlaceholderPattern(rPattern, ModelPartPattern::GetPlaceholderMap())
{
}


std::string ModelPartPattern::Apply(const ModelPart& rModelPart) const
{
    KRATOS_TRY
    ModelPartPattern::PlaceholderMap map;
    this->PopulatePlaceholderMap(map, rModelPart);
    return this->Apply(map);
    KRATOS_CATCH("");
}


void ModelPartPattern::PopulatePlaceholderMap(PlaceholderMap& rMap, const ModelPart& rModelPart) const
{
    // TODO: implement formatting, see the documentation in the header. @matekelemen
    const auto& r_pattern = this->GetPatternString();

    if (r_pattern.find("<model_part_name>") != r_pattern.npos) {
        rMap.emplace("<model_part_name>", rModelPart.Name());
    }

    if (r_pattern.find("<step>") != r_pattern.npos) {
        rMap.emplace("<step>", std::to_string(rModelPart.GetProcessInfo().GetValue(STEP)));
    }

    if (r_pattern.find("<time>") != r_pattern.npos) {
        // Hardcoded formatting - to be changed later
        std::stringstream stream;
        stream << std::scientific << std::setprecision(4) << rModelPart.GetProcessInfo().GetValue(TIME);
        rMap.emplace("<time>", stream.str());
    }

    if (r_pattern.find("<rank>") != r_pattern.npos) {
        rMap.emplace("<rank>", std::to_string(rModelPart.GetCommunicator().MyPID()));
    }
}


ModelPartPattern::ModelPartPattern(const std::string& rPattern, const PlaceholderMap& rPlaceholderMap)
    : PlaceholderPattern(rPattern, rPlaceholderMap)
{
}


CheckpointPattern::CheckpointPattern(const std::string& rPattern)
    : ModelPartPattern(rPattern, CheckpointPattern::GetPlaceholderMap())
{
}


void CheckpointPattern::PopulatePlaceholderMap(PlaceholderMap& rMap, const ModelPart& rModelPart) const
{
    KRATOS_TRY
    ModelPartPattern::PopulatePlaceholderMap(rMap, rModelPart);
    rMap.emplace("<path_id>", std::to_string(rModelPart.GetProcessInfo().GetValue(ANALYSIS_PATH)));
    KRATOS_CATCH("");
}


CheckpointPattern::PlaceholderMap CheckpointPattern::GetPlaceholderMap()
{
    auto output = ModelPartPattern::GetPlaceholderMap();
    output.emplace("<path_id>", RegexUtility::UnsignedInteger().first);
    return output;
}


} // namespace Kratos
