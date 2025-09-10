#!/usr/bin/env python3
"""
Game Utilities - Common functions for game name normalization and matching
"""

import os
import subprocess

def normalize_game_name(name):
    """Normalize game name for consistent matching across the application"""
    if not name:
        return ""

    # Remove roman numerals and convert to numbers
    normalized = name.replace(' III','3').replace(' II', ' 2').replace(" IV", '4').lower()

    # Remove specific characters: dash, colon, underscore, apostrophe
    for char in ['-', ':', '_', '/', '\\', '|', '!', '*', "'", '"', ',', '.',' ']:
        normalized = normalized.replace(char, '')
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

# convert_image_to_png_inplace function removed - use convert_image_to_png_replace instead

def convert_image_to_png_replace(file_path: str) -> tuple[str, str]:
    """
    Convert an image file to PNG format and return the new PNG file path and status.
    The original file is removed and replaced with a PNG file.
    
    Args:
        file_path: Path to the image file to convert
        
    Returns:
        Tuple of (new_file_path, status) where status is:
        - "already_png": File was already PNG format
        - "converted": File was successfully converted to PNG
        - "failed": Conversion failed
    """
    try:
        # Check if file is already PNG format
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension == '.png':
            return file_path, "already_png"  # Already PNG, no conversion needed
        
        # Create PNG path with .png extension
        png_path = os.path.splitext(file_path)[0] + '.png'
        
        # Convert to PNG
        if convert_image_to_png(file_path, png_path):
            # Remove original file
            os.remove(file_path)
            return png_path, "converted"  # Return the new PNG path
        else:
            return file_path, "failed"  # Return original path if conversion failed
            
    except Exception as e:
        print(f"Error converting image to PNG: {e}")
        return file_path, "failed"  # Return original path if error
