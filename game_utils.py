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
ARTICLE_PATTERN_END = re.compile(r",\s?(the|a|an|le|la|l'|un|une|el|los|las|de|der|die|das)(?=$|:)")
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

    if remove_paranthesis:
        normalized = remove_parentheses(normalized)
        
    normalized = remove_brackets(normalized)

    # Remove roman numerals and convert to numbers
    normalized = romain_vers_arabe_1_9(normalized).lower()

    # remove 1 number
    normalized = re.sub(r"\b1\b", "", normalized)

    # remove articles (the, a, an, le , )
    if remove_articles:
        normalized = ARTICLE_PATTERN_BEGIN.sub("", normalized)
        normalized = ARTICLE_PATTERN_END.sub("", normalized)    

    normalized = normalized.replace("&", "and")
    
    # Then keep only ASCII letters, numbers, and parentheses (removes accented chars and special chars)
    normalized = re.sub(r'[^a-zA-Z0-9()]', '', normalized)

    return normalized

def convert_image_to_png(input_path: str, output_path: str) -> bool:
    """
    Convert an image file to PNG format using ImageMagick.
    
    Args:
        input_path: Path to the input image file
        output_path: Path for the output PNG file
        
    Returns:
        True if conversion successful, False otherwise
    """
    try:
        # Use ImageMagick convert command to convert to PNG
        cmd = ['convert', input_path, output_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    except Exception as e:
        print(f"Error converting image to PNG: {e}")
        return False

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
    try:
        from PIL import Image
        import os
        
        # Determine if we need to change the file extension
        current_extension = os.path.splitext(file_path)[1].lower()
        needs_conversion = target_extension and current_extension != target_extension.lower()
        
        # Determine if we need to resize
        needs_resize = target_width > 0 or target_height > 0
        
        # If neither conversion nor resize is needed, return early
        if not needs_conversion and not needs_resize:
            return file_path, "already_correct"
        
        # Open the image
        with Image.open(file_path) as img:
            original_width, original_height = img.size
            processed_img = img
            
            # Resize if needed
            if needs_resize:
                # Calculate new dimensions
                if target_width > 0 and target_height > 0:
                    # Both width and height specified - resize to exact dimensions
                    new_width, new_height = target_width, target_height
                elif target_height > 0:
                    # Only height specified - maintain aspect ratio
                    aspect_ratio = original_width / original_height
                    new_width = int(target_height * aspect_ratio)
                    new_height = target_height
                elif target_width > 0:
                    # Only width specified - maintain aspect ratio
                    aspect_ratio = original_height / original_width
                    new_height = int(target_width * aspect_ratio)
                    new_width = target_width
                else:
                    new_width, new_height = original_width, original_height
                
                # Check if resize is actually needed
                if new_width != original_width or new_height != original_height:
                    processed_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    resize_msg = f"resized from {original_width}x{original_height} to {new_width}x{new_height}"
                else:
                    resize_msg = "no resize needed (already correct size)"
            else:
                new_width, new_height = original_width, original_height
                resize_msg = "no resize needed"
            
            # Determine the output file path
            if needs_conversion:
                # Create new path with target extension
                base_path = os.path.splitext(file_path)[0]
                output_path = base_path + target_extension
            else:
                # Keep the same path
                output_path = file_path
            
            # Save the processed image
            if target_extension and target_extension.lower() == '.jpg':
                # For JPEG, convert to RGB if needed and save with quality settings
                if processed_img.mode in ('RGBA', 'LA', 'P'):
                    # Create white background for transparency
                    rgb_img = Image.new('RGB', processed_img.size, (255, 255, 255))
                    if processed_img.mode == 'P':
                        processed_img = processed_img.convert('RGBA')
                    rgb_img.paste(processed_img, mask=processed_img.split()[-1] if processed_img.mode == 'RGBA' else None)
                    processed_img = rgb_img
                processed_img.save(output_path, 'JPEG', quality=95, optimize=True)
            elif target_extension and target_extension.lower() == '.png':
                # For PNG, save with optimization
                processed_img.save(output_path, 'PNG', optimize=True)
            else:
                # For other formats or no conversion, save with default settings
                processed_img.save(output_path, quality=95, optimize=True)
            
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
            
    except Exception as e:
        error_msg = str(e)
        if "cannot identify image file" in error_msg:
            print(f"❌ Error processing image: Downloaded file is not a valid image format")
        elif "No such file or directory" in error_msg:
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

