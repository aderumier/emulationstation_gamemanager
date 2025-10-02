#!/usr/bin/env python3
"""
Run the full Lemon64 spider
This will scrape all available pages from the Lemon64 database
"""

from lemon64_spider import Lemon64Spider
import time

def main():
    print("🚀 Starting FULL Lemon64 spider...")
    print("⚠️  This will take a while and scrape ALL available pages!")
    print("📊 Estimated time: 10-15 minutes for complete database")
    print("💾 Data will be saved to lemon64db.json")
    
    # Ask for confirmation
    response = input("\n🤔 Do you want to continue? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ Spider cancelled by user")
        return
    
    # Start the spider
    start_time = time.time()
    spider = Lemon64Spider()
    spider.run_spider(output_file="lemon64db.json", detailed_info=True)
    
    # Calculate runtime
    end_time = time.time()
    runtime = end_time - start_time
    minutes = int(runtime // 60)
    seconds = int(runtime % 60)
    
    print(f"\n⏱️  Total runtime: {minutes}m {seconds}s")
    print(f"📊 Final database contains {len(spider.games_db)} games")
    
    # Print some final statistics
    if spider.games_db:
        print("\n📈 Final Statistics:")
        
        # Count games by year
        years = {}
        for game in spider.games_db.values():
            if game.get('year'):
                years[game['year']] = years.get(game['year'], 0) + 1
        
        if years:
            print(f"   📅 Year range: {min(years.keys())} - {max(years.keys())}")
            most_common_year = max(years, key=years.get)
            print(f"   🏆 Most common year: {most_common_year} ({years[most_common_year]} games)")
        
        # Count games by publisher
        publishers = {}
        for game in spider.games_db.values():
            if game.get('publisher'):
                publishers[game['publisher']] = publishers.get(game['publisher'], 0) + 1
        
        if publishers:
            top_publisher = max(publishers, key=publishers.get)
            print(f"   🏢 Top publisher: {top_publisher} ({publishers[top_publisher]} games)")
        
        # Count games by genre
        genres = {}
        for game in spider.games_db.values():
            if game.get('genre'):
                genre = game['genre'].split(' - ')[0]  # Get main genre only
                genres[genre] = genres.get(genre, 0) + 1
        
        if genres:
            top_genre = max(genres, key=genres.get)
            print(f"   🎮 Top genre: {top_genre} ({genres[top_genre]} games)")
    
    print("\n✅ Spider completed successfully!")
    print("💾 Database saved as lemon64db.json")

if __name__ == "__main__":
    main()
