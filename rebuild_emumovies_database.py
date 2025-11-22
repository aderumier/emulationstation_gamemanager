#!/usr/bin/env python3
"""
Script to rebuild the entire EmuMovies database with progress tracking
"""

import asyncio
import sys
from emumovies_service import EmuMoviesService

async def rebuild_database():
    """Rebuild the entire EmuMovies database"""
    
    print("=" * 80)
    print("EmuMovies Database Full Rebuild")
    print("=" * 80)
    print()
    print("This will rebuild the entire EmuMovies database for all systems.")
    print("This may take a long time depending on the number of systems.")
    print()
    
    response = input("Do you want to continue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Cancelled.")
        return
    
    print()
    print("Starting database rebuild...")
    print()
    
    service = EmuMoviesService()
    
    # Progress callback
    def progress_callback(message, progress=None):
        if progress is not None:
            print(f"[{progress}%] {message}")
        else:
            print(f"{message}")
    
    # Build database for all systems (no target_system specified)
    result = await service.build_local_database(
        progress_callback=progress_callback,
        target_system=None  # Build all systems
    )
    
    print()
    if result.get('success'):
        print("=" * 80)
        print("✅ Database rebuild completed successfully!")
        print(f"   Systems processed: {result.get('systems_count')}")
        print(f"   Database path: {result.get('database_path')}")
        print("=" * 80)
    else:
        print("=" * 80)
        print("❌ Database rebuild failed!")
        print(f"   Error: {result.get('error')}")
        print("=" * 80)
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(rebuild_database())

