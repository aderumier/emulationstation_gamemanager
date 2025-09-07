#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import app

def debug_field_mapping():
    # Load the cache
    app.load_metadata_cache()
    
    # Get the game data for Berzerk (ID 116226)
    if '116226' in app.global_metadata_cache:
        game_data = app.global_metadata_cache['116226']
        game_element = game_data['game']
        
        print("=== LaunchBox Game Data ===")
        print(f"Name: {game_element.find('Name').text if game_element.find('Name') is not None else 'None'}")
        print(f"Overview: {game_element.find('Overview').text if game_element.find('Overview') is not None else 'None'}")
        print(f"Developer: {game_element.find('Developer').text if game_element.find('Developer') is not None else 'None'}")
        print(f"Publisher: {game_element.find('Publisher').text if game_element.find('Publisher') is not None else 'None'}")
        print(f"Genres: {game_element.find('Genres').text if game_element.find('Genres') is not None else 'None'}")
        print(f"CommunityRating: {game_element.find('CommunityRating').text if game_element.find('CommunityRating') is not None else 'None'}")
        print(f"MaxPlayers: {game_element.find('MaxPlayers').text if game_element.find('MaxPlayers') is not None else 'None'}")
        print()
        
        # Test the field mapping logic
        print("=== Field Mapping Test ===")
        mapping_config = {
            'Name': 'name',
            'Overview': 'desc', 
            'Developer': 'developer',
            'Publisher': 'publisher',
            'Genres': 'genre',
            'CommunityRating': 'rating',
            'MaxPlayers': 'players'
        }
        
        # Simulate the field processing logic
        best_match = {}
        for child in game_element:
            if child.tag in mapping_config:
                best_match[child.tag] = child.text
                print(f"✅ Found {child.tag}: {child.text}")
            else:
                print(f"❌ Skipped {child.tag}: {child.text}")
        
        print()
        print("=== Field Processing Simulation ===")
        selected_fields = ['Name', 'Overview', 'Developer', 'Publisher', 'Genres', 'CommunityRating', 'MaxPlayers']
        
        for launchbox_field, gamelist_field in mapping_config.items():
            print(f"Processing {launchbox_field} -> {gamelist_field}")
            
            # Skip field if not in selected fields (except launchboxid which is always processed)
            if selected_fields and launchbox_field not in selected_fields and launchbox_field != 'launchboxid':
                print(f"  ❌ Skipping {launchbox_field} (not in selected fields)")
                continue
                
            if launchbox_field in best_match and best_match[launchbox_field]:
                print(f"  ✅ Would update {gamelist_field} with: {best_match[launchbox_field]}")
            else:
                print(f"  ❌ No data for {launchbox_field}")
    else:
        print("Game 116226 not found")

if __name__ == "__main__":
    debug_field_mapping()
