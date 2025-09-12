#!/usr/bin/env python3
"""
Game Utilities - Common functions for game name normalization and matching
"""

import os
import subprocess
import json
import re
import unicodedata

def normalize_game_name(name):
    """Normalize game name for consistent matching across the application"""
    if not name:
        return ""

    # Remove non-Latin characters and normalize accented characters
    # First, normalize accented characters to their base forms
    normalized = unicodedata.normalize('NFD', name)

    # Remove roman numerals and convert to numbers
    normalized = normalized.replace(' III','3').replace(' II', ' 2').replace(" IV", '4').lower()

    # Then keep only ASCII letters and numbers (removes accented chars and special chars)
    normalized = re.sub(r'[^a-zA-Z0-9]', '', normalized)

#    # Remove specific characters: dash, colon, underscore, apostrophe
#    for char in ['-', ':', '_', '/', '\\', '|', '!', '*', "'", '"', ',', '.',' ']:
#        normalized = normalized.replace(char, '')
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



def convert_image_replace(file_path: str, target_extension: str = '.png') -> tuple[str, str]:
    """
    Convert an image file to the target format and return the new file path and status.
    The original file is removed and replaced with the target format file.
    
    Args:
        file_path: Path to the image file to convert
        target_extension: Target file extension (e.g., '.png', '.jpg')
        
    Returns:
        Tuple of (new_file_path, status) where status is:
        - "already_target": File was already in target format
        - "converted": File was successfully converted to target format
        - "failed": Conversion failed
    """
    try:
        # Check if file is already in target format
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension == target_extension.lower():
            return file_path, "already_target"  # Already in target format, no conversion needed
        
        # Create target path with target extension
        target_path = os.path.splitext(file_path)[0] + target_extension
        
        # Convert to target format
        if convert_image_to_format(file_path, target_path, target_extension):
            # Remove original file
            os.remove(file_path)
            return target_path, "converted"  # Return the new target path
        else:
            return file_path, "failed"  # Return original path if conversion failed
            
    except Exception as e:
        print(f"Error converting image to {target_extension}: {e}")
        return file_path, "failed"  # Return original path if error

def convert_image_to_format(input_path: str, output_path: str, target_extension: str) -> bool:
    """
    Convert an image file to the specified format using ImageMagick.
    
    Args:
        input_path: Path to the input image file
        output_path: Path for the output file
        target_extension: Target file extension (e.g., '.png', '.jpg')
        
    Returns:
        True if conversion successful, False otherwise
    """
    try:
        # Use ImageMagick convert command to convert to target format
        cmd = ['convert', input_path, output_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    except Exception as e:
        print(f"Error converting image to {target_extension}: {e}")
        return False

def should_convert_field(field_name: str, config: dict) -> tuple[bool, str]:
    """
    Check if a media field should be converted based on configuration.
    
    Args:
        field_name: Name of the media field (e.g., 'thumbnail', 'boxart')
        config: Configuration dictionary containing media_fields
        
    Returns:
        Tuple of (should_convert, target_extension) where:
        - should_convert: True if field should be converted
        - target_extension: Target extension if conversion needed, empty string otherwise
    """
    try:
        media_fields = config.get('media_fields', {})
        field_config = media_fields.get(field_name)
        
        if not field_config:
            return False, ""
        
        target_extension = field_config.get('target_extension')
        if target_extension:
            return True, target_extension
        
        return False, ""
        
    except Exception as e:
        print(f"Error checking field conversion config: {e}")
        return False, ""

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

