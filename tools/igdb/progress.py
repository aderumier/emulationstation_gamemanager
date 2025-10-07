#!/usr/bin/env python3
"""
IGDB Dump Progress Manager

This script allows you to check and manage the progress of the IGDB dump.
"""

import os
import sys
import json
from datetime import datetime

def load_progress():
    """Load progress from file"""
    progress_file = "var/db/igdb/dump/dump_progress.json"
    try:
        if os.path.exists(progress_file):
            with open(progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading progress: {e}")
    return {}

def show_progress():
    """Show current progress"""
    progress = load_progress()
    
    if not progress:
        print("📊 No progress file found - dump hasn't started yet")
        return
    
    print("📊 IGDB Dump Progress:")
    print("=" * 50)
    
    # Basic data progress
    print("📋 Basic Data:")
    print(f"   Platforms: {'✅' if progress.get('platforms_done') else '⏳'}")
    print(f"   Genres: {'✅' if progress.get('genres_done') else '⏳'}")
    print(f"   Game Modes: {'✅' if progress.get('game_modes_done') else '⏳'}")
    print(f"   Player Perspectives: {'✅' if progress.get('player_perspectives_done') else '⏳'}")
    print(f"   Companies: {'✅' if progress.get('companies_done') else '⏳'}")
    
    # Games progress
    print("\n🎯 Games:")
    total_games = progress.get('total_games', 0)
    games_offset = progress.get('games_offset', 0)
    print(f"   Total Games Dumped: {total_games}")
    print(f"   Current Offset: {games_offset}")
    
    if progress.get('interrupted'):
        print("   Status: 🛑 Interrupted")
    else:
        print("   Status: ✅ In Progress")
    
    # Last updated
    last_updated = progress.get('last_updated')
    if last_updated:
        try:
            dt = datetime.fromisoformat(last_updated)
            print(f"   Last Updated: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        except:
            print(f"   Last Updated: {last_updated}")

def clear_progress():
    """Clear progress file"""
    progress_file = "var/db/igdb/dump/dump_progress.json"
    try:
        if os.path.exists(progress_file):
            os.remove(progress_file)
            print("🗑️ Progress file cleared")
        else:
            print("📊 No progress file found")
    except Exception as e:
        print(f"❌ Error clearing progress: {e}")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python progress.py [show|clear]")
        print("  show  - Show current progress")
        print("  clear - Clear progress file (start fresh)")
        return
    
    command = sys.argv[1].lower()
    
    if command == "show":
        show_progress()
    elif command == "clear":
        clear_progress()
    else:
        print(f"Unknown command: {command}")
        print("Usage: python progress.py [show|clear]")

if __name__ == '__main__':
    main()
