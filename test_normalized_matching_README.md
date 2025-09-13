# Normalized Game Name Matching Test Script

This script compares two different normalization methods for game names from a gamelist.xml file against LaunchBox Metadata.xml entries.

## Usage

```bash
python3 test_normalized_matching.py <gamelist.xml> [output.csv] [threshold]
```

### Arguments:
- `gamelist.xml`: Path to the gamelist.xml file to test
- `output.csv`: Output CSV file (optional, defaults to "normalized_matching_results.csv")
- `threshold`: Similarity threshold for partial matches (optional, defaults to 0.98)

## Examples

```bash
# Test NES games with default threshold
python3 test_normalized_matching.py var/gamelists/nes/gamelist.xml nes_results.csv

# Test MAME games with custom threshold
python3 test_normalized_matching.py var/gamelists/mame/gamelist.xml mame_results.csv 0.85

# Test with default output filename and threshold
python3 test_normalized_matching.py var/gamelists/vectrex/gamelist.xml
```

### Similarity Threshold:
- **0.98-1.0**: Very strict matching (near-exact matches only)
- **0.90-0.97**: Strict matching (high confidence matches)
- **0.80-0.89**: Moderate matching (good similarity)
- **0.70-0.79**: Loose matching (somewhat similar)
- **<0.70**: Very loose matching (low confidence)

## Output Format

The script generates a CSV file with the following columns:

1. **Original Name**: The game name from gamelist.xml
2. **Cleaned Name**: The name after removing parentheses (e.g., "Super Mario Bros. 3 (USA)" → "Super Mario Bros. 3")
3. **Normalized (OLD)**: The normalized version using the old method
4. **Normalized (NEW)**: The normalized version using the new method
5. **Match OLD**: 1 if a match was found with old method, 0 if not
6. **Match NEW**: 1 if a match was found with new method, 0 if not
7. **Type OLD**: "main" or "alternate" for old method match
8. **Type NEW**: "main" or "alternate" for new method match
9. **Matched OLD**: The actual matched name from LaunchBox (old method)
10. **Matched NEW**: The actual matched name from LaunchBox (new method)
11. **Improvement**: "BETTER", "WORSE", "SAME", or "DIFFERENT"
12. **Partial Match**: 1 if a partial match was found via similarity search, 0 if not
13. **Similarity Score**: The similarity score (0.0-1.0) for partial matches, empty for exact matches
14. **Partial Matched Name**: The matched name from similarity search, empty for exact matches
15. **Partial Match Type**: "main" or "alternate" for partial matches, empty for exact matches

## How It Works

1. **Platform Detection**: Extracts platform from gamelist path (e.g., `var/gamelists/nes/gamelist.xml` → `nes`)
2. **Platform Mapping**: Uses `var/config/config.json` to map platform to LaunchBox name (e.g., `nes` → `Nintendo Entertainment System`)
3. **Metadata Loading**: Loads LaunchBox Metadata.xml and filters games by platform
4. **Index Building**: Creates O(1) lookup indexes for both normalization methods (main names and alternate names)
5. **Parentheses Removal**: Removes text between parentheses from ROM names before normalization
6. **Dual Normalization**: Tests both old and new normalization methods using pre-built indexes
7. **Exact Matching**: Performs fast exact matches against both main names and alternate names for each method
8. **Similarity Search**: For games that don't match exactly, performs similarity search using partitioned indexes
9. **Comparison**: Generates a detailed comparison report with improvement analysis and partial matches

## Performance Optimization

The script uses **indexed lookups** for optimal performance:
- **O(1) Lookup Time**: Instead of linear search through all metadata games
- **Pre-built Indexes**: Both normalization methods are indexed once at startup
- **Memory Efficient**: Indexes store only normalized names and references
- **Scalable**: Performance remains constant regardless of metadata size

This makes the script efficient even with large metadata files (100k+ games).

## Performance Benchmarking

The script includes comprehensive timing measurements:
- **Index Building Time**: Time to build lookup indexes for both methods
- **Method Timing**: Separate timing for old and new normalization methods
- **Per-Game Timing**: Average time per game in milliseconds
- **Speed Comparison**: Percentage difference between methods
- **Total Processing Time**: Complete end-to-end timing

### Timing Metrics:
- **Index Building**: One-time cost for building lookup tables
- **Old Method Time**: Time for old normalization + matching
- **New Method Time**: Time for new normalization + matching  
- **Speed Difference**: Relative performance comparison (+/- %)

### Normalization-Only Timing:
- **Cumulative Time**: Total time spent only on normalization (excluding matching)
- **Per-Game Time**: Average normalization time per individual game
- **Speed Difference**: Direct comparison of normalization function performance

This helps you evaluate both accuracy and performance trade-offs between normalization methods, with detailed breakdown of where time is spent.

## Similarity Search

For games that don't match exactly with either normalization method, the script performs similarity search:

### Features:
- **Partitioned Index**: Games are partitioned by first character for faster searching
- **Multi-metric Similarity**: Uses token overlap, sequence similarity, and Levenshtein distance
- **Configurable Threshold**: Adjustable similarity threshold (0.0-1.0)
- **Fast Pre-filtering**: Length and character overlap filters before expensive similarity calculations
- **Performance Optimized**: ~27x faster than brute force search

### Similarity Metrics:
- **Token Overlap (50%)**: Word-based matching using Jaccard similarity
- **Sequence Similarity (30%)**: Character sequence matching using difflib
- **Levenshtein Distance (20%)**: Edit distance normalized by string length

### Performance Results:
- **MAME Dataset (2,985 games)**: 6.6 seconds for similarity search
- **Partitioned Search**: Only searches games starting with the same character
- **Pre-filtering**: Reduces candidates by ~90% before full similarity calculation

## Parentheses Removal

The script automatically removes text between parentheses from ROM names before normalization:
- **Purpose**: ROM names often contain region codes, version info, or metadata in parentheses
- **Examples**: 
  - "Super Mario Bros. 3 (USA)" → "Super Mario Bros. 3"
  - "1942 (Revision B)" → "1942"
  - "Donkey Kong (Japan, Set 1)" → "Donkey Kong"
- **Impact**: Dramatically improves match rates by focusing on core game names
- **Regex**: Handles nested parentheses correctly

## Normalization Methods

### Old Method (`normalize_game_name`)
- Removes non-Latin characters and normalizes accented characters
- Converts roman numerals (III → 3, II → 2, IV → 4)
- Keeps only ASCII letters, numbers, and parentheses
- Example: "Super Mario Bros. 3 (USA)" → "supermariobros3(usa)"

### New Method (`normalize_search_term`)
- Converts to lowercase and replaces underscores with spaces
- Removes articles (a, an, the) from beginning and after commas
- Removes punctuation and normalizes spaces
- Handles Unicode normalization and accent removal
- Example: "Super Mario Bros. 3 (USA)" → "super mario bros 3 usa"

## Requirements

- Python 3.6+
- `var/config/config.json` (for platform mapping)
- `var/db/launchbox/Metadata.xml` (LaunchBox metadata)
- Valid gamelist.xml file

## CSV Output

The script outputs a properly formatted CSV file that can be opened in:
- Microsoft Excel
- Google Sheets
- LibreOffice Calc
- Any text editor or spreadsheet application

The CSV format makes it easy to:
- Sort and filter results
- Create charts and graphs
- Perform further analysis
- Share results with others

## Sample Output

```
=== COMPARISON SUMMARY ===
Total games tested: 2985
Similarity threshold: 0.85

PERFORMANCE TIMING:
  Index building time: 0.034 seconds
  Similarity index time: 0.018 seconds
  Old method time: 0.015 seconds
  New method time: 0.021 seconds
  Similarity search time: 6.633 seconds
  Total processing time: 6.722 seconds

NORMALIZATION TIMING:
  Old normalization cumulative: 0.003252 seconds
  New normalization cumulative: 0.006035 seconds
  Old normalization per game: 0.001 ms
  New normalization per game: 0.002 ms
  Normalization speed difference: +85.6%

OLD NORMALIZATION:
  Matches found: 2626
  Match rate: 88.0%
  Time per game: 0.00 ms

NEW NORMALIZATION:
  Matches found: 2578
  Match rate: 86.4%
  Time per game: 0.01 ms

PARTIAL MATCHES (Similarity >= 0.85):
  Partial matches found: 7
  Partial match rate: 0.2%
  Combined match rate: 86.6%

IMPROVEMENTS:
  Better matches: 6
  Worse matches: 54
  Same results: 2925
  Net improvement: -48
  Speed difference: +47.1%

=== GAMES WHERE NEW METHOD IS BETTER (6) ===
✓/✗ BETTER  Age Of Heroes - Silkroad 2 (v0.63 - 2001/02/07)
    Cleaned: Age Of Heroes - Silkroad 2
    OLD: ageofheroessilkroad2 → No match
    NEW: age of heroes silkroad 2 → The Age of Heroes: Silkroad 2

✓/✗ BETTER  Bradley Trainer
    OLD: bradleytrainer → No match
    NEW: bradley trainer → The Bradley Trainer

=== GAMES WHERE OLD METHOD IS BETTER (54) ===
✗/✓ WORSE   Alien3: The Gun (World)
    Cleaned: Alien3: The Gun
    OLD: alien3thegun → Alien 3: The Gun
    NEW: alien3 the gun → No match

✗/✓ WORSE   Battle Zone (rev 2)
    Cleaned: Battle Zone
    OLD: battlezone → Battlezone
    NEW: battle zone → No match

=== SAMPLE RESULTS ===
✓/✓ SAME   Donkey Kong (USA)
    Cleaned: Donkey Kong
    OLD: donkeykong
    NEW: donkey kong
    OLD Match: Donkey Kong
    NEW Match: Donkey Kong
```
