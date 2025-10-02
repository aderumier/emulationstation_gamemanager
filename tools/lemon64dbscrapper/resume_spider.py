#!/usr/bin/env python3
"""
Resume Spider Management Script
Allows starting, stopping, and resuming the Lemon64 spider
"""

import sys
import os
import json
import time
from lemon64_spider import Lemon64Spider

def show_status():
    """Show current spider status"""
    spider = Lemon64Spider()
    if spider.load_progress():
        progress = spider.progress_data
        print("📊 Spider Status:")
        print(f"   Status: {progress['status']}")
        print(f"   Last page: {progress['last_page_count']}")
        print(f"   Last offset: {progress['last_page_offset']}")
        print(f"   Games collected: {progress['total_games_collected']}")
        if progress['last_run_timestamp']:
            last_run = time.ctime(progress['last_run_timestamp'])
            print(f"   Last run: {last_run}")
    else:
        print("📊 No progress file found - spider has not been run yet")

def clear_progress():
    """Clear progress and start fresh"""
    spider = Lemon64Spider()
    spider.clear_progress()
    print("✅ Progress cleared - next run will start fresh")

def resume_spider(max_pages=None, detailed_info=True):
    """Resume spider from last position"""
    spider = Lemon64Spider()
    print("🔄 Resuming spider...")
    spider.run_spider(max_pages=max_pages, detailed_info=detailed_info, resume=True)

def start_fresh(max_pages=None, detailed_info=True):
    """Start spider fresh (clear progress first)"""
    spider = Lemon64Spider()
    spider.clear_progress()
    print("🆕 Starting fresh spider...")
    spider.run_spider(max_pages=max_pages, detailed_info=detailed_info, resume=False)

def main():
    if len(sys.argv) < 2:
        print("Usage: python resume_spider.py <command> [options]")
        print("\nCommands:")
        print("  status                    - Show current spider status")
        print("  resume [--max-pages=N]    - Resume from last position")
        print("  fresh [--max-pages=N]     - Start fresh (clear progress)")
        print("  clear                     - Clear progress file")
        print("  test                      - Run test with 3 pages")
        print("\nOptions:")
        print("  --max-pages=N             - Limit to N pages")
        print("  --no-details              - Disable detailed info extraction")
        return
    
    command = sys.argv[1]
    
    # Parse options
    max_pages = None
    detailed_info = True
    
    for arg in sys.argv[2:]:
        if arg.startswith("--max-pages="):
            max_pages = int(arg.split("=")[1])
        elif arg == "--no-details":
            detailed_info = False
    
    if command == "status":
        show_status()
    elif command == "resume":
        resume_spider(max_pages, detailed_info)
    elif command == "fresh":
        start_fresh(max_pages, detailed_info)
    elif command == "clear":
        clear_progress()
    elif command == "test":
        start_fresh(3, detailed_info)
    else:
        print(f"❌ Unknown command: {command}")
        print("Use 'python resume_spider.py' for help")

if __name__ == "__main__":
    main()


