#!/usr/bin/env python3
"""
Game Utilities - Common functions for game name normalization and matching
"""

import os
import subprocess
import json
import re
import unicodedata
from functools import lru_cache

import jellyfish

ARTICLE_PATTERN_BEGIN = re.compile(r"^\b(|a|an|the|le|la|l'|un|une|el|los|las|de|der|die|das)\b")
ARTICLE_PATTERN_END = re.compile(r",\s?(the|a|an|le|la|l'|un|une|el|los|las|de|der|die|das)(?=\s|$|:)")
NON_WORD_SPACE_PATTERN = re.compile(r"[^\w\s]")
MULTIPLE_SPACE_PATTERN = re.compile(r"\s+")
WORD_TOKEN_PATTERN = re.compile(r"\b\w+\b")

# This caches results to avoid repeated normalization of the same search term
@lru_cache(maxsize=1024)

def remove_parentheses(text):
    """Remove text between parentheses including the parentheses"""
     # Remove text between parentheses (including nested parentheses)
    return re.sub(r'\s*\([^()]*(?:\([^()]*\)[^()]*)*\)', '', text).strip()

def remove_brackets(text):
    """Remove text between square brackets including the brackets"""
    
    # Remove text between square brackets
    return re.sub(r'\s*\[[^\[\]]*\]', '', text).strip()

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
    # Exclude "I" when it's part of an abbreviation (preceded or followed by a period)
    # For "I" specifically, require it's not part of an abbreviation pattern like "G.I." or "U.S.A."
    pattern = r'(?<![A-Za-z.])(?:IX|VIII|VII|VI|V|IV|III|II|(?!\.)I(?!\.))\b(?![A-Za-z.])'

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

    # Remove parentheses first (before moving articles)
    if remove_paranthesis:
        name = remove_parentheses(name)
        
    name = remove_brackets(name)
    
    # When remove_articles=False, convert trailing articles (after comma) to beginning after removing parentheses
    # This way we can properly match ", The" at the end even if it was followed by parentheses or separators
    if not remove_articles:
        # Match patterns: ",The", ",A", ",La", ",Le", ",L'", ",Der", ",Die", ",Das" at the end or followed by separator (- or :)
        # Order matters: match longer patterns first (L' before L)
        patterns = [
            (r',\s*The\s*(?:$|[-:])', 'The'),
            (r',\s*La\s*(?:$|[-:])', 'La'),
            (r',\s*Le\s*(?:$|[-:])', 'Le'),
            (r",\s*L'\s*(?:$|[-:])", "L'"),
            (r',\s*Der\s*(?:$|[-:])', 'Der'),
            (r',\s*Die\s*(?:$|[-:])', 'Die'),
            (r',\s*Das\s*(?:$|[-:])', 'Das'),
            (r',\s*A\s*(?:$|[-:])', 'A'),
        ]
        
        for pattern, article in patterns:
            matched = re.search(pattern, name, flags=re.IGNORECASE)
            if matched:
                # Remove the matched pattern (including the separator if present)
                # The pattern matches ", The" followed by end or separator, so we replace it with empty string
                name = re.sub(pattern, '', name, flags=re.IGNORECASE)
                # Clean up any extra spaces or separators that might remain
                name = re.sub(r'\s*[-:]\s*', ' ', name).strip()
                # Add article at the beginning
                if article == "L'":
                    # L' doesn't have a space after it
                    name = f"{article}{name.strip()}"
                else:
                    # Other articles have a space after them
                    name = f"{article} {name.strip()}"
                break
    
    normalized = name

    # Remove roman numerals and convert to numbers
    normalized = romain_vers_arabe_1_9(normalized).lower()

    # remove 1 number (but not when it's part of a larger number like 1,000)
    # Don't remove "1" if it's followed by a comma and digits (like "1,000")
    normalized = re.sub(r"\b1\b(?!,\d)", "", normalized)

    # remove articles (the, a, an, le , )
    if remove_articles:
        normalized = ARTICLE_PATTERN_BEGIN.sub("", normalized)
        normalized = ARTICLE_PATTERN_END.sub("", normalized)    

    normalized = normalized.replace("&", "and")
    
    # Then keep only ASCII letters, numbers, and parentheses (removes accented chars and special chars)
    normalized = re.sub(r'[^a-zA-Z0-9()]', '', normalized)

    return normalized

def should_process_field(field_name: str, config: dict) -> tuple[bool, str, int, int]:
    """
    Check if a media field should be converted and/or resized based on configuration.
    
    Args:
        field_name: Name of the media field (e.g., 'thumbnail', 'boxart')
        config: Configuration dictionary containing media_fields
        
    Returns:
        Tuple of (should_process, target_extension, width, height) where:
        - should_process: True if field needs any processing (convert or resize)
        - target_extension: Target extension if conversion needed, empty string otherwise
        - width: Target width (0 if not specified)
        - height: Target height (0 if not specified)
    """
    try:
        # Skip image processing for video fields
        if field_name == 'video':
            return False, "", 0, 0
        
        media_fields = config.get('media_fields', {})
        field_config = media_fields.get(field_name)
        
        if not field_config:
            return False, "", 0, 0
        
        target_extension = field_config.get('target_extension', '')
        width = field_config.get('width', 0)
        height = field_config.get('height', 0)
        
        # Process if either conversion or resize is needed
        needs_conversion = bool(target_extension)
        needs_resize = width > 0 or height > 0
        
        if needs_conversion or needs_resize:
            return True, target_extension, width, height
        
        return False, "", 0, 0
        
    except Exception as e:
        print(f"Error checking field processing config: {e}")
        return False, "", 0, 0

def convert_and_resize_image_replace(file_path: str, target_extension: str = None, target_width: int = 0, target_height: int = 0) -> tuple[str, str]:
    """
    Convert and/or resize an image file in a single operation and return the new file path and status.
    The original file is replaced with the processed version.
    Uses ImageMagick for processing.
    
    Args:
        file_path: Path to the image file to process
        target_extension: Target file extension (e.g., '.png', '.jpg') - None to keep original
        target_width: Target width (0 to maintain aspect ratio)
        target_height: Target height (0 to maintain aspect ratio)
        
    Returns:
        Tuple of (new_file_path, status) where status is:
        - "already_correct": File was already in correct format and size
        - "converted": File was converted to target format
        - "resized": File was resized
        - "converted_and_resized": File was both converted and resized
        - "failed": Processing failed
    """
    import subprocess
    import os
    
    try:
        # Determine if we need to change the file extension
        current_extension = os.path.splitext(file_path)[1].lower()
        needs_conversion = target_extension and current_extension != target_extension.lower()
        
        # Determine if we need to resize
        needs_resize = target_width > 0 or target_height > 0
        
        # If neither conversion nor resize is needed, return early
        if not needs_conversion and not needs_resize:
            return file_path, "already_correct"
        
        # Get original image dimensions for resize check (only if resize is needed)
        original_width = 0
        original_height = 0
        if needs_resize:
            try:
                # Use ImageMagick identify to get dimensions
                identify_cmd = ['identify', '-format', '%wx%h', file_path]
                result = subprocess.run(identify_cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    dimensions = result.stdout.strip().split('x')
                    if len(dimensions) == 2:
                        original_width = int(dimensions[0])
                        original_height = int(dimensions[1])
            except Exception as e:
                print(f"⚠️ Warning: Could not get image dimensions: {e}")
        
        # Determine the output file path
        if needs_conversion:
            # Create new path with target extension
            base_path = os.path.splitext(file_path)[0]
            output_path = base_path + target_extension
        else:
            # Use temporary file for in-place operations, then replace original
            base_path = os.path.splitext(file_path)[0]
            output_path = base_path + '.tmp' + current_extension
        
        # Build ImageMagick convert command
        cmd = ['convert', file_path]
        
        # Handle transparency for JPEG conversion
        if needs_conversion and target_extension and target_extension.lower() in ['.jpg', '.jpeg']:
            # Check if image has transparency (RGBA, LA, or P mode)
            try:
                identify_alpha_cmd = ['identify', '-format', '%[channels]', file_path]
                alpha_result = subprocess.run(identify_alpha_cmd, capture_output=True, text=True, timeout=10)
                if alpha_result.returncode == 0 and 'a' in alpha_result.stdout.lower():
                    # Image has alpha channel, add white background and remove alpha
                    cmd.extend(['-background', 'white', '-alpha', 'remove'])
            except Exception:
                # If we can't determine, assume it might have transparency and add the flags anyway
                cmd.extend(['-background', 'white', '-alpha', 'remove'])
        
        # Add resize operation if needed
        if needs_resize:
            if target_width > 0 and target_height > 0:
                # Both width and height specified - resize to exact dimensions (no aspect ratio preservation)
                # Use '!' suffix to force exact dimensions
                resize_spec = f"{target_width}x{target_height}!"
                new_width = target_width
                new_height = target_height
            elif target_height > 0:
                # Only height specified - maintain aspect ratio
                resize_spec = f"x{target_height}"
                if original_width > 0 and original_height > 0:
                    aspect_ratio = original_width / original_height
                    new_width = int(target_height * aspect_ratio)
                    new_height = target_height
                else:
                    new_width = 0
                    new_height = target_height
            elif target_width > 0:
                # Only width specified - maintain aspect ratio
                resize_spec = f"{target_width}x"
                if original_width > 0 and original_height > 0:
                    aspect_ratio = original_height / original_width
                    new_height = int(target_width * aspect_ratio)
                    new_width = target_width
                else:
                    new_width = target_width
                    new_height = 0
            else:
                resize_spec = None
                new_width = original_width
                new_height = original_height
            
            if resize_spec:
                # Check if resize is actually needed
                if original_width > 0 and original_height > 0:
                    if new_width == original_width and new_height == original_height:
                        # Already correct size - check if we still need conversion
                        if not needs_conversion:
                            return file_path, "already_correct"
                        resize_msg = "no resize needed (already correct size)"
                    else:
                        cmd.extend(['-resize', resize_spec])
                        resize_msg = f"resized from {original_width}x{original_height} to {new_width}x{new_height}"
                else:
                    # Can't determine dimensions, proceed with resize
                    cmd.extend(['-resize', resize_spec])
                    resize_msg = f"resized to {resize_spec}"
        else:
            resize_msg = "no resize needed"
        
        # Add quality setting for JPEG
        if needs_conversion and target_extension and target_extension.lower() in ['.jpg', '.jpeg']:
            cmd.extend(['-quality', '95'])
        
        # Add PNG optimization
        if needs_conversion and target_extension and target_extension.lower() == '.png':
            cmd.extend(['-strip'])
        
        # Add output file
        cmd.append(output_path)
        
        # Execute ImageMagick convert command
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print(f"❌ ImageMagick convert failed: {result.stderr}")
            return file_path, "failed"
        
        # If we used a temporary file for in-place operation, replace original
        if not needs_conversion and output_path != file_path:
            try:
                os.replace(output_path, file_path)
                output_path = file_path
            except Exception as e:
                print(f"⚠️ Warning: Could not replace original file: {e}")
                return file_path, "failed"
        
        # Delete the original file if we created a new one with different extension
        if needs_conversion and output_path != file_path:
            try:
                os.remove(file_path)
                print(f"🗑️ Removed original file: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"⚠️ Warning: Could not remove original file {file_path}: {e}")
        
        # Determine status message
        if needs_conversion and needs_resize:
            status = "converted_and_resized"
            print(f"✅ Converted to {target_extension} and {resize_msg}")
        elif needs_conversion:
            status = "converted"
            print(f"✅ Converted to {target_extension}")
        elif needs_resize:
            status = "resized"
            print(f"✅ {resize_msg.capitalize()}")
        else:
            status = "already_correct"
        
        return output_path, status
            
    except subprocess.TimeoutExpired:
        print(f"❌ Error processing image: ImageMagick command timed out")
        return file_path, "failed"
    except FileNotFoundError:
        print(f"❌ Error processing image: ImageMagick not found. Please install ImageMagick.")
        return file_path, "failed"
    except Exception as e:
        error_msg = str(e)
        if "No such file or directory" in error_msg:
            print(f"❌ Error processing image: File not found: {file_path}")
        else:
            print(f"❌ Error processing image: {error_msg}")
        return file_path, "failed"

def resize_image_replace(file_path: str, target_width: int = 0, target_height: int = 0) -> tuple[str, str]:
    """
    Resize an image file and return the new file path and status.
    The original file is replaced with the resized version.
    
    Args:
        file_path: Path to the image file to resize
        target_width: Target width (0 to maintain aspect ratio)
        target_height: Target height (0 to maintain aspect ratio)
        
    Returns:
        Tuple of (new_file_path, status) where status is:
        - "already_correct": File was already the correct size
        - "resized": File was successfully resized
        - "failed": Resize failed
    """
    # Use the combined function for backward compatibility
    return convert_and_resize_image_replace(file_path, None, target_width, target_height)

def get_file_extension(file_path: str) -> str:
    """
    Get the file extension from a file path.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File extension in lowercase (e.g., '.png', '.jpg')
    """
    return os.path.splitext(file_path)[1].lower()

def needs_conversion(file_path: str, target_extension: str) -> bool:
    """
    Check if a file needs conversion to the target extension.
    
    Args:
        file_path: Path to the file
        target_extension: Target extension (e.g., '.png', '.jpg')
        
    Returns:
        True if file needs conversion, False otherwise
    """
    current_extension = get_file_extension(file_path)
    return current_extension != target_extension.lower()

def load_similarity_config():
    """Load similarity algorithm configuration from config.json"""
    try:
        with open('var/config/config.json', 'r') as f:
            config = json.load(f)
        return config.get('similarity', {})
    except Exception as e:
        print(f"Error loading similarity config: {e}")
        return {'algorithm': 'jaro_winkler'}

def calculate_similarity(str1: str, str2: str, algorithm: str = None) -> float:
    """
    Calculate similarity between two strings using the specified algorithm.
    
    Args:
        str1: First string to compare
        str2: Second string to compare
        algorithm: Algorithm to use (if None, uses cookie preference or config default)
        
    Returns:
        Similarity score between 0.0 and 1.0 (higher is more similar)
    """
    if not algorithm:
        # Try to get from cookie first, then fall back to config
        try:
            from flask import request
            algorithm = request.cookies.get('similarity_algorithm', 'jaro_winkler')
        except:
            # Fallback to config if not in Flask context
            config = load_similarity_config()
            algorithm = config.get('algorithm', 'jaro_winkler')
    
    # Normalize strings for comparison
    str1 = str1.lower().strip() if str1 else ""
    str2 = str2.lower().strip() if str2 else ""
    
    if not str1 or not str2:
        return 0.0
    
    if str1 == str2:
        return 1.0
    
    try:
        if algorithm == 'jaro_winkler':
            return jellyfish.jaro_winkler_similarity(str1, str2)
        elif algorithm == 'damerau_levenshtein':
            # Convert distance to similarity (0-1 scale)
            max_len = max(len(str1), len(str2))
            if max_len == 0:
                return 1.0
            distance = jellyfish.damerau_levenshtein_distance(str1, str2)
            return 1.0 - (distance / max_len)
        elif algorithm == 'levenshtein':
            # Convert distance to similarity (0-1 scale)
            max_len = max(len(str1), len(str2))
            if max_len == 0:
                return 1.0
            distance = jellyfish.levenshtein_distance(str1, str2)
            return 1.0 - (distance / max_len)
        elif algorithm == 'jaro':
            # Jaro distance (without Winkler modification)
            return jellyfish.jaro_similarity(str1, str2)
        elif algorithm == 'hamming':
            # Hamming distance - only works for strings of equal length
            if len(str1) != len(str2):
                return 0.0
            if len(str1) == 0:
                return 1.0
            distance = jellyfish.hamming_distance(str1, str2)
            return 1.0 - (distance / len(str1))
        elif algorithm == 'match_rating':
            # Match Rating Approach - returns 1 if codes match, 0 otherwise
            return 1.0 if jellyfish.match_rating_comparison(str1, str2) else 0.0
        else:
            # Fallback to Jaro-Winkler
            return jellyfish.jaro_winkler_similarity(str1, str2)
    except Exception as e:
        print(f"Error calculating similarity with {algorithm}: {e}")
        # Fallback to Jaro-Winkler
        return jellyfish.jaro_winkler_similarity(str1, str2)

