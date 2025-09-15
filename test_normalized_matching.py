#!/usr/bin/env python3
"""
Test script to compare normalized game name matching against LaunchBox Metadata.xml
Usage: python test_normalized_matching.py <gamelist.xml> [output.csv]
"""

import sys
import os
import xml.etree.ElementTree as ET
import re
import unicodedata
import json
import csv
import time
from typing import List, Dict, Tuple
from difflib import SequenceMatcher
import jellyfish

ARTICLE_PATTERN_BEGIN = re.compile(r"^\b(|a|an|the|le|la|l'|un|une|el|los|las|de|der|die|das)\b")
ARTICLE_PATTERN_END = re.compile(r",\s?(the|a|an|le|la|l'|un|une|el|los|las|de|der|die|das)(?=$|:)")
NON_WORD_SPACE_PATTERN = re.compile(r"[^\w\s]")
MULTIPLE_SPACE_PATTERN = re.compile(r"\s+")
WORD_TOKEN_PATTERN = re.compile(r"\b\w+\b")

def romain_vers_arabe_1_9(texte: str) -> str:
    mapping = {
        "I": "1",
        "II": "2",
        "III": "3",
        "IV": "4",
        "V": "5",
        "VI": "6",
        "VII": "7",
        "VIII": "8",
        "IX": "9"
    }

    # Regex : capture uniquement I–IX, isolés, insensible à la casse
    pattern = r'(?<![A-Za-z])\b(?:IX|VIII|VII|VI|V|IV|III|II|I)\b(?![A-Za-z])'

    def remplacement(match):
        romain = match.group(0).upper()  # normalisation
        return mapping[romain]

    return re.sub(pattern, remplacement, texte, flags=re.IGNORECASE)

def normalize_game_name(name, remove_paranthesis=True, remove_articles=True):
    """Normalize game name for consistent matching across the application (OLD VERSION)"""
    if not name:
        return ""

    # Remove non-Latin characters and normalize accented characters
    # First, normalize accented characters to their base forms
    normalized = unicodedata.normalize('NFD', name)
    name = "".join(c for c in normalized if not unicodedata.combining(c))

    normalized = remove_brackets(normalized)

    # Remove roman numerals and convert to numbers
    normalized = romain_vers_arabe_1_9(normalized).lower()

    # remove 1 number
    normalized = re.sub(r"\b1\b", "", normalized)

    # remove articles (the, a, an, le , )
    normalized = ARTICLE_PATTERN_BEGIN.sub("", normalized)
    normalized = ARTICLE_PATTERN_END.sub("", normalized)    

    # Then keep only ASCII letters, numbers, and parentheses (removes accented chars and special chars)
    normalized = re.sub(r'[^a-zA-Z0-9()]', '', normalized)

    return normalized

def normalize_search_term(name, remove_articles=True, remove_punctuation=True):
    """Normalize search term using the new function (NEW VERSION)"""
    # Import the patterns from game_utils

    
    if not name:
        return ""

    # Unicode normalization and accent removal
    normalized = unicodedata.normalize("NFD", name)
    name = "".join(c for c in normalized if not unicodedata.combining(c))


    normalized = remove_brackets(normalized)

    # Lower and replace underscores with spaces
    name = name.lower().replace("_", " ")

    # Remove articles (combined if possible)
    if remove_articles:
        name = ARTICLE_PATTERN_BEGIN.sub("", name)
        name = ARTICLE_PATTERN_END.sub("", name)

    # Remove roman numerals and convert to numbers
    name = romain_vers_arabe_1_9(normalized)
    # remove 1 number
    name = re.sub(r"\b1\b", "", name)


    # Remove punctuation and normalize spaces in one step
    if remove_punctuation:
        name = NON_WORD_SPACE_PATTERN.sub(" ", name)
        name = MULTIPLE_SPACE_PATTERN.sub(" ", name)

    return name.strip()

def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings"""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

def calculate_title_similarity(search_normalized: str, game_name: str) -> float:
    """
    Calculate similarity between search term and game name using multiple metrics.
    Returns a score between 0 and 1, where 1 is a perfect match.
    """
    game_normalized = normalize_search_term(game_name, remove_articles=True)

    # Exact match gets the highest score
    if search_normalized == game_normalized:
        return 1.0

    # Split into tokens for word-based matching
    search_tokens = set(WORD_TOKEN_PATTERN.findall(search_normalized.lower()))
    game_tokens = set(WORD_TOKEN_PATTERN.findall(game_normalized.lower()))

    # Calculate token overlap ratio
    if search_tokens and game_tokens:
        intersection = search_tokens & game_tokens
        union = search_tokens | game_tokens
        token_overlap_ratio = len(intersection) / len(union)
    else:
        token_overlap_ratio = 0.0

    # Calculate sequence similarity (better for longer strings)
    sequence_ratio = SequenceMatcher(
        None, search_normalized, game_normalized
    ).ratio()

    # Calculate Levenshtein distance (normalized by max length)
    max_len = max(len(search_normalized), len(game_normalized))
    if max_len > 0:
        levenshtein_ratio = 1 - (
            levenshtein_distance(search_normalized, game_normalized) / max_len
        )
    else:
        levenshtein_ratio = 1.0

    # Token overlap is most important for game titles
    final_score = (
        token_overlap_ratio * 0.5 + sequence_ratio * 0.3 + levenshtein_ratio * 0.2
    )

    return final_score

def build_similarity_index(metadata_games):
    """Build a partitioned index of normalized names for faster similarity search"""
    similarity_index = {}
    
    for game in metadata_games:
        main_name = game.get('Name', '')
        if main_name:
            normalized_main = normalize_game_name(main_name)
            first_char = normalized_main[0].lower() if normalized_main else 'other'
            if first_char not in similarity_index:
                similarity_index[first_char] = []
            similarity_index[first_char].append({
                'name': main_name,
                'normalized': normalized_main,
                'type': 'main'
            })
        
        # Add alternate names
        alternate_names = game.get('AlternateNames', [])
        for alt_name in alternate_names:
            normalized_alt = normalize_game_name(alt_name)
            first_char = normalized_alt[0].lower() if normalized_alt else 'other'
            if first_char not in similarity_index:
                similarity_index[first_char] = []
            similarity_index[first_char].append({
                'name': alt_name,
                'normalized': normalized_alt,
                'type': 'alternate'
            })
    
    return similarity_index

def find_similarity_matches(gamelist_name, similarity_index, threshold=0.0):
    """Find the best similarity match by searching only in the matching partition"""
    cleaned_name = remove_parentheses(gamelist_name)

    normalized_name = normalize_game_name(cleaned_name)
    
    if not normalized_name:
        return []
    
    # Get the first character to search in the right partition
    first_char = normalized_name[0].lower()
    
    # Search only in the matching partition
    if first_char not in similarity_index:
        return []
    
    best_match = None
    best_similarity = 0.0
    best_jaro_similarity = 0.0
    
    # Search through ALL items in the matching partition only
    for item in similarity_index[first_char]:
        # Calculate both similarity scores
        similarity = calculate_title_similarity(normalized_name, item['normalized'])
        jaro_similarity = jellyfish.jaro_winkler_similarity(normalized_name, item['normalized'])
        
        if similarity > best_similarity:
            best_similarity = similarity
            best_jaro_similarity = jaro_similarity
            best_match = {
                'name': item['name'],
                'similarity': similarity,
                'jaro_similarity': jaro_similarity,
                'type': item['type']
            }
    
    # Return the best match if it meets the threshold
    if best_match and best_similarity >= threshold:
        return [best_match]
    
    return []

def parse_gamelist_xml(file_path):
    """Parse gamelist.xml file and return list of games"""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        games = []
        
        for game in root.findall('game'):
            game_data = {}
            
            # Parse each field
            for field in game:
                tag = field.tag
                text = field.text.strip() if field.text else ''
                
                if tag == 'name':
                    game_data['name'] = text
                elif tag == 'path':
                    game_data['path'] = text
                # Add other fields as needed
            
            if 'name' in game_data:
                games.append(game_data)
        
        return games
    except Exception as e:
        print(f"Error parsing gamelist.xml: {e}")
        return []

def parse_launchbox_metadata(metadata_path, target_platform):
    """Parse LaunchBox Metadata.xml file and return list of games for target platform"""
    try:
        tree = ET.parse(metadata_path)
        root = tree.getroot()
        games = []
        
        # Load games for the specific platform
        all_games = root.findall('.//Game')
        print(f"Found {len(all_games)} total Game entries in Metadata.xml")
        
        platform_games_count = 0
        for game in all_games:
            db_id = game.find('DatabaseID')
            game_platform = game.find('Platform')
            
            if (db_id is not None and db_id.text and 
                game_platform is not None and game_platform.text == target_platform):
                db_id_text = db_id.text
                game_data = {'DatabaseID': db_id_text, 'Platform': game_platform.text}
                
                # Parse game fields
                for child in game:
                    tag = child.tag
                    text = child.text.strip() if child.text else ''
                    if tag not in ['DatabaseID', 'Platform']:
                        game_data[tag] = text
                
                games.append(game_data)
                platform_games_count += 1
        
        # Load alternate names for games in this platform
        all_alternate_names = root.findall('.//GameAlternateName')
        print(f"Found {len(all_alternate_names)} total GameAlternateName entries in Metadata.xml")
        
        platform_alt_names_count = 0
        for alt_name in all_alternate_names:
            game_id = alt_name.find('GameID')
            alt_name_text = alt_name.find('AlternateName')
            
            if (game_id is not None and game_id.text and 
                alt_name_text is not None and alt_name_text.text):
                game_id_text = game_id.text
                alt_name_value = alt_name_text.text.strip()
                
                # Find the game with this DatabaseID and add alternate name
                for game in games:
                    if game.get('DatabaseID') == game_id_text:
                        if 'AlternateNames' not in game:
                            game['AlternateNames'] = []
                        game['AlternateNames'].append(alt_name_value)
                        platform_alt_names_count += 1
                        break
        
        print(f"Found {platform_games_count} games and {platform_alt_names_count} alternate names for platform: {target_platform}")
        return games
        
    except Exception as e:
        print(f"Error parsing Metadata.xml: {e}")
        return []

def build_metadata_indexes(metadata_games):
    """Build simplified indexes for both normalization methods"""
    print("Building metadata indexes for both normalization methods...")
    
    # Indexes for old normalization method (merged main + alternate)
    old_index = {}
    
    # Indexes for new normalization method (merged main + alternate)
    new_index = {}
    
    for i, game in enumerate(metadata_games):
        # Index main name with both methods
        main_name = game.get('Name', '')
        if main_name:
            # Old normalization
            old_normalized_main = normalize_game_name(main_name)
            if old_normalized_main:
                old_index[old_normalized_main] = main_name
            
            # New normalization
            new_normalized_main = normalize_search_term(main_name)
            if new_normalized_main:
                new_index[new_normalized_main] = main_name
        
        # Index alternate names with both methods
        alternate_names = game.get('AlternateNames', [])
        for alt_name in alternate_names:
            # Old normalization
            old_normalized_alt = normalize_game_name(alt_name)
            if old_normalized_alt:
                old_index[old_normalized_alt] = alt_name
            
            # New normalization
            new_normalized_alt = normalize_search_term(alt_name)
            if new_normalized_alt:
                new_index[new_normalized_alt] = alt_name
    
    print(f"Built indexes: {len(old_index)} old names (main + alternate)")
    print(f"Built indexes: {len(new_index)} new names (main + alternate)")
    
    return {
        'old': old_index,
        'new': new_index
    }

def remove_parentheses(text):
    """Remove text between parentheses including the parentheses"""
    import re
    # Remove text between parentheses (including nested parentheses)
    return re.sub(r'\s*\([^()]*(?:\([^()]*\)[^()]*)*\)', '', text).strip()

def remove_brackets(text):
    """Remove text between square brackets including the brackets"""
    import re
    # Remove text between square brackets
    return re.sub(r'\s*\[[^\[\]]*\]', '', text).strip()

def find_match_in_metadata_indexed(gamelist_name, metadata_indexes, use_new_normalization=False):
    """Find if a gamelist game name matches any metadata game name using pre-built indexes"""
    # Remove parentheses and brackets from ROM name before normalization
    cleaned_gamelist_name = remove_parentheses(gamelist_name)
    cleaned_gamelist_name = remove_brackets(cleaned_gamelist_name)
    
    if use_new_normalization:
        normalized_gamelist_name = normalize_search_term(cleaned_gamelist_name)
        index = metadata_indexes['new']
    else:
        normalized_gamelist_name = normalize_game_name(cleaned_gamelist_name)
        index = metadata_indexes['old']
    
    # Try exact match with simplified index (O(1) lookup)
    if normalized_gamelist_name in index:
        matched_name = index[normalized_gamelist_name]
        return True, 'main', matched_name  # We don't distinguish between main/alternate anymore
    
    return False, None, None

def load_platform_mapping():
    """Load platform mapping from config.json"""
    try:
        with open('var/config/config.json', 'r') as f:
            config = json.load(f)
        return config.get('systems', {})
    except Exception as e:
        print(f"Error loading config.json: {e}")
        return {}

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_normalized_matching.py <gamelist.xml> [output.csv] [threshold]")
        print("Example: python test_normalized_matching.py var/gamelists/nes/gamelist.xml results.csv 0.0")
        print("  threshold: Minimum similarity threshold for partial matches (default: 0.0 = best match)")
        sys.exit(1)
    
    gamelist_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "normalized_matching_results.csv"
    similarity_threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
    
    # Check if gamelist exists
    if not os.path.exists(gamelist_path):
        print(f"Error: Gamelist file not found: {gamelist_path}")
        sys.exit(1)
    
    # Determine platform from gamelist path (assume it's in var/gamelists/<platform>/gamelist.xml)
    platform = None
    path_parts = gamelist_path.split(os.sep)
    if 'gamelists' in path_parts:
        gamelists_index = path_parts.index('gamelists')
        if gamelists_index + 1 < len(path_parts):
            platform = path_parts[gamelists_index + 1]
    
    if not platform:
        print("Error: Could not determine platform from gamelist path")
        print("Expected path format: var/gamelists/<platform>/gamelist.xml")
        sys.exit(1)
    
    print(f"Platform detected: {platform}")
    
    # Load platform mapping to get LaunchBox platform name
    platform_mapping = load_platform_mapping()
    launchbox_platform = platform_mapping.get(platform, {}).get('launchbox', platform)
    print(f"LaunchBox platform: {launchbox_platform}")
    
    # Look for Metadata.xml in var/db/launchbox/
    metadata_path = "var/db/launchbox/Metadata.xml"
    if not os.path.exists(metadata_path):
        print(f"Error: Metadata.xml not found at: {metadata_path}")
        sys.exit(1)
    
    # Parse gamelist
    print(f"Parsing gamelist: {gamelist_path}")
    gamelist_games = parse_gamelist_xml(gamelist_path)
    print(f"Found {len(gamelist_games)} games in gamelist")
    
    # Parse metadata
    print(f"Parsing metadata: {metadata_path}")
    metadata_games = parse_launchbox_metadata(metadata_path, launchbox_platform)
    print(f"Found {len(metadata_games)} games in metadata for platform {launchbox_platform}")
    
    if not metadata_games:
        print(f"Warning: No metadata games found for platform '{platform}'")
        print("Available platforms in metadata:")
        # Show available platforms
        try:
            tree = ET.parse(metadata_path)
            root = tree.getroot()
            platforms = set()
            for game in root.findall('.//Game'):
                platform_elem = game.find('Platform')
                if platform_elem is not None and platform_elem.text:
                    platforms.add(platform_elem.text)
            for p in sorted(platforms):
                print(f"  - {p}")
        except:
            pass
        sys.exit(1)
    
    # Build indexes for both normalization methods
    print("Building metadata indexes for both normalization methods...")
    index_start_time = time.time()
    metadata_indexes = build_metadata_indexes(metadata_games)
    index_time = time.time() - index_start_time
    
    # Test matching with both versions using indexes
    print("Testing normalized matching with both methods using indexes...")
    results_old = []
    
    # Time the old normalization method
    old_method_start = time.time()
    old_normalization_time = 0
    for gamelist_game in gamelist_games:
        original_name = gamelist_game.get('name', '')
        cleaned_name = remove_parentheses(original_name)
        cleaned_name = remove_brackets(cleaned_name)
        
        # Time just the normalization
        norm_start = time.time()
        normalized_name_old = normalize_game_name(cleaned_name)
        old_normalization_time += time.time() - norm_start
        
        match_found_old, match_type_old, matched_name_old = find_match_in_metadata_indexed(original_name, metadata_indexes, use_new_normalization=False)
        
        # Store results for old method
        results_old.append({
            'original_name': original_name,
            'cleaned_name': cleaned_name,
            'normalized_name_old': normalized_name_old,
            'match_found_old': 1 if match_found_old else 0,
            'match_type_old': match_type_old or '',
            'matched_name_old': matched_name_old or '',
        })
    old_method_time = time.time() - old_method_start
    
    # Time the new normalization method
    new_method_start = time.time()
    new_normalization_time = 0
    for i, gamelist_game in enumerate(gamelist_games):
        original_name = gamelist_game.get('name', '')
        cleaned_name = remove_parentheses(original_name)
        cleaned_name = remove_brackets(cleaned_name)
        
        # Time just the normalization
        norm_start = time.time()
        normalized_name_new = normalize_search_term(cleaned_name)
        new_normalization_time += time.time() - norm_start
        
        match_found_new, match_type_new, matched_name_new = find_match_in_metadata_indexed(original_name, metadata_indexes, use_new_normalization=True)
        
        # Update results with new method data
        results_old[i].update({
            'normalized_name_new': normalized_name_new,
            'match_found_new': 1 if match_found_new else 0,
            'match_type_new': match_type_new or '',
            'matched_name_new': matched_name_new or '',
            'improvement': 'BETTER' if match_found_new and not results_old[i]['match_found_old'] else 'WORSE' if results_old[i]['match_found_old'] and not match_found_new else 'SAME' if results_old[i]['match_found_old'] == match_found_new else 'DIFFERENT'
        })
    new_method_time = time.time() - new_method_start
    
    # Build similarity index for faster searching
    print("Building similarity index...")
    similarity_index_start = time.time()
    similarity_index = build_similarity_index(metadata_games)
    similarity_index_time = time.time() - similarity_index_start
    
    # Find similarity matches for games that didn't match exactly with new method
    print(f"Searching for similarity matches (threshold: {similarity_threshold})...")
    similarity_start = time.time()
    partial_matches = []
    
    for i, result in enumerate(results_old):
        if not result['match_found_new']:  # Only for games that didn't match exactly
            original_name = result['original_name']
            similarity_matches = find_similarity_matches(original_name, similarity_index, similarity_threshold)
            if similarity_matches:
                best_match = similarity_matches[0]  # Get the best match
                partial_matches.append({
                    'original_name': original_name,
                    'cleaned_name': result['cleaned_name'],
                    'normalized_name': result['normalized_name_new'],
                    'matched_name': best_match['name'],
                    'similarity': best_match['similarity'],
                    'jaro_similarity': best_match['jaro_similarity'],
                    'match_type': best_match['type']
                })
    
    similarity_time = time.time() - similarity_start
    
    # Create mapping from original names to partial matches for CSV output
    partial_matches_map = {pm['original_name']: pm for pm in partial_matches}
    
    results = results_old
    
    # Write results to CSV file
    print(f"Writing results to: {output_path}")
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow([
            'Original Name',
            'Cleaned Name',
            'Normalized (OLD)',
            'Normalized (NEW)',
            'Match OLD',
            'Match NEW',
            'Type OLD',
            'Type NEW',
            'Matched OLD',
            'Matched NEW',
            'Improvement',
            'Partial Match',
            'Custom Similarity Score',
            'Jaro-Winkler Score',
            'Partial Matched Name',
            'Partial Match Type'
        ])
        
        # Write results
        for result in results:
            # Check if this game has a partial match
            partial_match = partial_matches_map.get(result['original_name'])
            has_partial_match = 1 if partial_match else 0
            custom_similarity_score = partial_match['similarity'] if partial_match else ''
            jaro_similarity_score = partial_match['jaro_similarity'] if partial_match else ''
            partial_matched_name = partial_match['matched_name'] if partial_match else ''
            partial_match_type = partial_match['match_type'] if partial_match else ''
            
            writer.writerow([
                result['original_name'],
                result['cleaned_name'],
                result['normalized_name_old'],
                result['normalized_name_new'],
                result['match_found_old'],
                result['match_found_new'],
                result['match_type_old'],
                result['match_type_new'],
                result['matched_name_old'],
                result['matched_name_new'],
                result['improvement'],
                has_partial_match,
                custom_similarity_score,
                jaro_similarity_score,
                partial_matched_name,
                partial_match_type
            ])
    
    # Print summary
    total_games = len(results)
    matches_found_old = sum(1 for r in results if r['match_found_old'])
    matches_found_new = sum(1 for r in results if r['match_found_new'])
    match_rate_old = (matches_found_old / total_games * 100) if total_games > 0 else 0
    match_rate_new = (matches_found_new / total_games * 100) if total_games > 0 else 0
    
    improvements = sum(1 for r in results if r['improvement'] == 'BETTER')
    regressions = sum(1 for r in results if r['improvement'] == 'WORSE')
    same_results = sum(1 for r in results if r['improvement'] == 'SAME')
    
    # Find all differences between normalization methods
    better_matches = [r for r in results if r['improvement'] == 'BETTER']
    worse_matches = [r for r in results if r['improvement'] == 'WORSE']
    different_matches = [r for r in results if r['improvement'] == 'DIFFERENT']
    
    print(f"\n=== COMPARISON SUMMARY ===")
    print(f"Total games tested: {total_games}")
    print(f"Similarity threshold: {similarity_threshold}")
    print(f"")
    print(f"PERFORMANCE TIMING:")
    print(f"  Index building time: {index_time:.3f} seconds")
    print(f"  Similarity index time: {similarity_index_time:.3f} seconds")
    print(f"  Old method time: {old_method_time:.3f} seconds")
    print(f"  New method time: {new_method_time:.3f} seconds")
    print(f"  Similarity search time: {similarity_time:.3f} seconds")
    print(f"  Total processing time: {index_time + similarity_index_time + old_method_time + new_method_time + similarity_time:.3f} seconds")
    print(f"")
    print(f"NORMALIZATION TIMING:")
    print(f"  Old normalization cumulative: {old_normalization_time:.6f} seconds")
    print(f"  New normalization cumulative: {new_normalization_time:.6f} seconds")
    print(f"  Old normalization per game: {old_normalization_time/total_games*1000:.3f} ms")
    print(f"  New normalization per game: {new_normalization_time/total_games*1000:.3f} ms")
    print(f"  Normalization speed difference: {((new_normalization_time - old_normalization_time) / old_normalization_time * 100):+.1f}%")
    print(f"")
    print(f"OLD NORMALIZATION:")
    print(f"  Matches found: {matches_found_old}")
    print(f"  Match rate: {match_rate_old:.1f}%")
    print(f"  Time per game: {old_method_time/total_games*1000:.2f} ms")
    print(f"")
    print(f"NEW NORMALIZATION:")
    print(f"  Matches found: {matches_found_new}")
    print(f"  Match rate: {match_rate_new:.1f}%")
    print(f"  Time per game: {new_method_time/total_games*1000:.2f} ms")
    print(f"")
    print(f"BEST SIMILARITY MATCHES (Threshold >= {similarity_threshold}):")
    print(f"  Best matches found: {len(partial_matches)}")
    print(f"  Best match rate: {len(partial_matches)/total_games*100:.1f}%")
    print(f"  Combined match rate: {(matches_found_new + len(partial_matches))/total_games*100:.1f}%")
    print(f"")
    print(f"IMPROVEMENTS:")
    print(f"  Better matches: {improvements}")
    print(f"  Worse matches: {regressions}")
    print(f"  Same results: {same_results}")
    print(f"  Net improvement: {improvements - regressions}")
    print(f"  Speed difference: {((new_method_time - old_method_time) / old_method_time * 100):+.1f}%")
    print(f"")
    
    # Show detailed differences
    if better_matches:
        print(f"=== GAMES WHERE NEW METHOD IS BETTER ({len(better_matches)}) ===")
        for result in better_matches:
            print(f"✓/✗ BETTER  {result['original_name']}")
            if result['cleaned_name'] != result['original_name']:
                print(f"    Cleaned: {result['cleaned_name']}")
            print(f"    OLD: {result['normalized_name_old']} → No match")
            print(f"    NEW: {result['normalized_name_new']} → {result['matched_name_new']}")
            print()
    
    if worse_matches:
        print(f"=== GAMES WHERE OLD METHOD IS BETTER ({len(worse_matches)}) ===")
        for result in worse_matches:
            print(f"✗/✓ WORSE   {result['original_name']}")
            if result['cleaned_name'] != result['original_name']:
                print(f"    Cleaned: {result['cleaned_name']}")
            print(f"    OLD: {result['normalized_name_old']} → {result['matched_name_old']}")
            print(f"    NEW: {result['normalized_name_new']} → No match")
            print()
    
    if different_matches:
        print(f"=== GAMES WHERE METHODS MATCH DIFFERENTLY ({len(different_matches)}) ===")
        for result in different_matches:
            print(f"✓/✓ DIFFERENT {result['original_name']}")
            if result['cleaned_name'] != result['original_name']:
                print(f"    Cleaned: {result['cleaned_name']}")
            print(f"    OLD: {result['normalized_name_old']} → {result['matched_name_old']}")
            print(f"    NEW: {result['normalized_name_new']} → {result['matched_name_new']}")
            print()
    
    # Show best similarity matches
    if partial_matches:
        print(f"=== BEST SIMILARITY MATCHES ({len(partial_matches)}) ===")
        for match in partial_matches[:10]:  # Show first 10 best matches
            print(f"✓ BEST  {match['original_name']}")
            if match['cleaned_name'] != match['original_name']:
                print(f"    Cleaned: {match['cleaned_name']}")
            print(f"    Normalized: {match['normalized_name']}")
            print(f"    Matched: {match['matched_name']} (similarity: {match['similarity']:.3f}, {match['match_type']})")
            print()
        if len(partial_matches) > 10:
            print(f"    ... and {len(partial_matches) - 10} more best matches")
            print()
    
    print(f"Results saved to: {output_path}")
    
    # Show some examples
    print(f"\n=== SAMPLE RESULTS ===")
    for i, result in enumerate(results[:10]):  # Show first 10
        status_old = "✓" if result['match_found_old'] else "✗"
        status_new = "✓" if result['match_found_new'] else "✗"
        improvement = result['improvement']
        print(f"{status_old}/{status_new} {improvement:6} {result['original_name']}")
        if result['cleaned_name'] != result['original_name']:
            print(f"    Cleaned: {result['cleaned_name']}")
        print(f"    OLD: {result['normalized_name_old']}")
        print(f"    NEW: {result['normalized_name_new']}")
        if result['match_found_old'] or result['match_found_new']:
            print(f"    OLD Match: {result['matched_name_old']}")
            print(f"    NEW Match: {result['matched_name_new']}")
        print()

if __name__ == "__main__":
    main()
