/// @author Máté Kelemen

#pragma once

// --- Core Includes ---
#include "includes/kratos_export_api.h"
#include "includes/model_part.h"

// --- STL Includes ---
#include <regex>
#include <vector>
#include <map>
#include <filesystem>


namespace Kratos {


///@addtogroup WRApp
///@{
///@name Kratos Classes
///@{


/** @brief Static-only utility class for common regexes.
 *
 *  @details Static access to pairs of regex patterns (as @c std::string)
 *           and their associated regexes (as @c std::regex).
 *  @note No instances are allowed to be constructed from this class.
 */
class RegexUtility
{
public:
    ///@name Inquiry
    ///@{

    /** @brief Get a string-regex pair representing an integer.
     *
     *  @details Matches the following pattern:
     *           - optional leading '-'
     *           - 0 or [1-9]+[0-9]*
     *
     *  @return A pair of
     *          - @c std::string of a regex pattern representing an @a integer.
     *          - @c std::regex of that string.
     *  @note This function can be called safely from other static functions.
     */
    static std::pair<std::string,std::regex> Integer();

    /** @brief Get a string-regex pair representing an unsigned integer.
     *
     *  @details Matches the following pattern:
     *           - 0 or [1-9]+[0-9]*
     *
     *  @return A pair of
     *          - @c std::string of a regex pattern representing an <em>unsigned integer</em>.
     *          - @c std::regex of that string.
     *  @note This function can be called safely from other static functions.
     */
    static std::pair<std::string,std::regex> UnsignedInteger();

    /** @brief Get a string-regex pair representing an integer.
     *
     *  @details Matches the following pattern:
     *           - optional leading '-'
     *           - whole part identical to @ref RegexUtility::Integer
     *           - optional decimal point, optionally followed by the fractional part [0-9]*
     *           - optional scientific notation suffix [eE][\+-][0-9]+
     *
     *  @return A pair of
     *          - @c std::string of a regex pattern representing a <em>floating point</em>
     *            number in decimal or scientific notation.
     *          - @c std::regex of that string.
     *
     *  @note This function can be called safely from other static functions.
     */
    static std::pair<std::string,std::regex> FloatingPoint();

    ///@}

private:
    ///@name Life Cycle
    ///@{

    /// @brief Deleted default constructor (no instances of this class are allowed).
    RegexUtility() = delete;

    /// @brief Deleted move constructor (no instances of this class are allowed).
    RegexUtility(RegexUtility&& rOther) = delete;

    /// @brief Deleted copy constructor (no instances of this class are allowed).
    RegexUtility(const RegexUtility& rOther) = delete;

    ///@}
}; // class RegexUtility


/** @brief A class for interfacing placeholders and regular expressions.
 *
 *  @note placeholders should be separated by literals, otherwise
 *        regex will probably not capture them as you'd expect.
 *        BAD example:
 *            pattern:    "<placeholder_1><placeholder_2>"
 *            string:     "abcdefg"
 *            result:
 *                "<placeholder_1>" : "abcdef"
 *                "<placeholder_2>" : "g"
 *        CORRECT example:
 *            pattern:    "<placeholder_1>d<placeholder_2>"
 *            string:     "abcdefg"
 *            result:
 *                "<placeholder_1>" : "abc"
 *                "<placeholder_2>" : "efg"
 *
 *  @note placeholders not present in the pattern are discarded,
 *        and won't be keys in @ref PlaceholderPattern::Match.
 */
class KRATOS_API(WR_APPLICATION) PlaceholderPattern
{
public:
    ///@name Type Definitions
    ///@{

    using PlaceholderMap = std::map<std::string,std::string>;

    using PlaceholderGroupMap = std::map<std::string,std::vector<std::size_t>>;

    using MatchType = std::map<std::string,std::vector<std::string>>;

    using PathType = std::filesystem::path;

    KRATOS_CLASS_POINTER_DEFINITION(PlaceholderPattern);

    ///@}
    ///@name Life Cycle
    ///@{

    /// Default constructor
    PlaceholderPattern() = default;

    /** @brief Construct from a placeholder pattern and its associated map.
     *  @param rPattern Pattern string with placeholders.
     *  @param rPlaceholders Pairs of placeholders and their corresponding regex strings.
     *                       Example: {{"<name>", ".+"}, {"<identifier>", "[0-9]+"}}
     *
     *  @warning The corresponding regexes must be bare, not containing groups (checked)
     *           or position constraints such as line begin or end modifiers (not checked).
     */
    PlaceholderPattern(const std::string& rPattern,
                       const PlaceholderMap& rPlaceholderMap);

    /// Move constructor
    PlaceholderPattern(PlaceholderPattern&& rOther) = default;

    /// Copy constructor
    PlaceholderPattern(const PlaceholderPattern& rOther) = default;

    virtual ~PlaceholderPattern() = default;

    ///@}
    ///@name Operators
    ///@{

    /// @brief Move assignment operator
    PlaceholderPattern& operator=(PlaceholderPattern&& rOther) = default;

    /// @brief Copy assignment operator
    PlaceholderPattern& operator=(const PlaceholderPattern& rOther) = default;

    ///@}
    ///@name Operations
    ///@{

    /// @brief Check whether a string satisfies the pattern
    bool IsAMatch(const std::string& rString) const;

    /** @brief Find all placeholders' values in the input string.
     *
     *  @param rString String matching the input pattern.
     *  @return Map associating a vector of strings, i.e. the values
     *          of placeholders in the input string, to the placeholders.
     *
     *  @note The returned placeholder values appear in the same order
     *        they do in the input pattern.
     */
    MatchType Match(const std::string& rString) const;

    /** @brief Substitute values in the stored pattern.
     *
     *  @details Return a copy of the pattern that has its placeholders replaced
     *           with the corresponding values specified in the input map.
     *  @param rPlaceholderValueMap string - string map associating values to placeholders
     *                              {"palceholder" : "placeholder_value"}
     */
    std::string Apply(const PlaceholderMap& rPlaceholderValueMap) const;

    ///@}
    ///@name Inquiry
    ///@{

    /// @brief Get the regex for the input pattern.
    const std::regex& GetRegex() const;

    /// @brief Get the string representation of the regex.
    const std::string& GetRegexString() const;

    /// @brief Get the pattern with placeholders.
    const std::string& GetPatternString() const;

    ///@}

private:
    ///@name Member Variables
    ///@{

    std::string mPattern;

    // Placeholders and their assigned group indices in the pattern
    PlaceholderGroupMap mPlaceholderGroupMap;

    std::string mRegexString;

    std::regex mRegex;

    ///@}
    ///@name Private Operations
    ///@{

    /// Escape characters in the input that interfere with regex syntax
    static std::string FormatRegexLiteral(const std::string& rLiteral);

    ///@}
}; // class PlaceholderPattern


/** @brief A class for working with formatted strings related to @ref ModelParts.
 *
 *  @details Operations on strings with the following placeholders are supported:
 *           - <model_part_name>
 *           - <step>
 *           - <time>
 *           - <rank>
 *           See @ref PlaceholderPattern for supported functionalities. Other
 *           placeholders can be added at compile time by tweaking the construction
 *           of the static member @ref ModelPartPattern::mModelpartPlaceholderMap.
 */
class KRATOS_API(WR_APPLICATION) ModelPartPattern : public PlaceholderPattern
{
public:
    ///@name Type Definitions
    ///@{

    KRATOS_CLASS_POINTER_DEFINITION(ModelPartPattern);

    ///@}
    ///@name Life Cycle
    ///@{

    ModelPartPattern() = default;

    ModelPartPattern(const std::string& rPattern);

    ModelPartPattern(ModelPartPattern&& rOther) = default;

    ModelPartPattern(const ModelPartPattern& rOther) = default;

    ///@}
    ///@name Operators
    ///@{

    using PlaceholderPattern::operator=;

    ///@}
    ///@name Operations
    ///@{

    using PlaceholderPattern::Apply;

    /** @brief Substitute values from the specified @ref ModelPart in the stored pattern.
     *
     *  @param rModelPart: Model part to extract the values of placeholders from.
     *  @note @p rModelPart must store @ref STEP and @ref TIME.
     *  @todo Add support for string formatting. Options are:
     *        - @c snprintf from the C STL (security issues due to allowing the user to freely specify the format)
     *        - @c fmt::format (requires fmtlib)
     *        - @c std::format (==fmtlib adopted in the standard, requires C++20)
     *        - @c boost::format (requires boost)
     */
    std::string Apply(const ModelPart& rModelPart) const;

    /** @brief Collect all file/directory paths that match the pattern.
     *  @tparam TOutputIterator: output iterator with value type constructible from @ref PathType.
     *  @note the search begins from the filesystem root if the pattern is an absolute path,
     *        otherwise it begins from @c cwd.
     */
    template <class TOutputIterator>
    void Glob(TOutputIterator it) const;

    ///@}

protected:
    ///@name Protected Methods
    ///@{

    /// @brief Forwarding constructor for derived classes.
    ModelPartPattern(const std::string& rPattern, const PlaceholderMap& rPlaceholderMap);

    static const PlaceholderMap& GetPlaceholderMap();

    ///@}

private:
    ///@name Static Member Variables
    ///@{

    static PlaceholderMap mModelPartPlaceholderMap;

    ///@}
}; // class ModelPartPattern


/** @brief A class for working with formatted strings related to @ref Checkpoint.
 *
 *  @details An extension of @ref ModelPartPattern with <path_id>. Operations on
 *           strings with the following placeholders are supported:
 *           - <model_part_name>
 *           - <step>
 *           - <time>
 *           - <rank>
 *           - <path_id>
 *           See @ref PlaceholderPattern for supported functionalities. Other
 *           placeholders can be added at compile time by tweaking the construction
 *           of the static member @ref CheckpointPattern::mCheckpointPlaceholderMap.
 */
class KRATOS_API(WR_APPLICATION) CheckpointPattern : public ModelPartPattern
{
public:
    ///@name Type Definitions
    ///@{

    KRATOS_CLASS_POINTER_DEFINITION(CheckpointPattern);

    ///@}
    ///@name Life Cycle
    ///@{

    CheckpointPattern() = default;

    CheckpointPattern(const std::string& rPattern);

    CheckpointPattern(CheckpointPattern&& rOther) = default;

    CheckpointPattern(const CheckpointPattern& rOther) = default;

    ///@}
    ///@name Operators
    ///@{

    using ModelPartPattern::operator=;

    ///@}
    ///@name Operations
    ///@{

    using PlaceholderPattern::Apply;

    /** @brief Substitute values from the specified @ref ModelPart and path ID into the stored pattern.
     *
     *  @param rModelPart: Model part to extract the values of placeholders from.
     *  @param PathID: path ID of the checkpoint.
     *  @note @p rModelPart must store @ref STEP and @ref TIME.
     */
    std::string Apply(const ModelPart& rModelPart, std::size_t PathID) const;

    ///@}

protected:
    ///@name Protected Operations
    ///@{

    static const PlaceholderMap& GetPlaceholderMap();

    ///@}

private:
    ///@name Member Variables
    ///@{

    static PlaceholderMap mCheckpointPlaceholderMap;

    ///@}
}; // class CheckpointPattern


///@}
///@}


} // namespace Kratos

#include "wrapp/utils/impl/PatternUtility_impl.hpp"
