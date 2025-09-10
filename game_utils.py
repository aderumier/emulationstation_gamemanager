#!/usr/bin/env python3
"""
Game Utilities - Common functions for game name normalization and matching
"""

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
