#!/usr/bin/env python3
"""
Lemon64 Database Viewer
View and search the scraped Lemon64 database
"""

import json
import sys
from typing import Dict, List

class Lemon64Viewer:
    def __init__(self, db_file: str = "lemon64db.json"):
        self.db_file = db_file
        self.games = {}
        self.load_database()
    
    def load_database(self):
        """Load the database from JSON file"""
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                self.games = json.load(f)
            print(f"📂 Loaded {len(self.games)} games from {self.db_file}")
        except FileNotFoundError:
            print(f"❌ Database file {self.db_file} not found")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error loading database: {e}")
            sys.exit(1)
    
    def search_games(self, query: str) -> List[Dict]:
        """Search games by title"""
        query = query.lower()
        results = []
        
        for game in self.games.values():
            if query in game.get('title', '').lower():
                results.append(game)
        
        return results
    
    def filter_by_year(self, year: int) -> List[Dict]:
        """Filter games by release year"""
        results = []
        
        for game in self.games.values():
            if game.get('year') == year:
                results.append(game)
        
        return results
    
    def filter_by_publisher(self, publisher: str) -> List[Dict]:
        """Filter games by publisher"""
        publisher = publisher.lower()
        results = []
        
        for game in self.games.values():
            if publisher in game.get('publisher', '').lower():
                results.append(game)
        
        return results
    
    def get_statistics(self):
        """Get database statistics"""
        stats = {
            'total_games': len(self.games),
            'years': {},
            'publishers': {},
            'genres': {},
            'ratings': []
        }
        
        for game in self.games.values():
            # Count by year
            year = game.get('year')
            if year:
                stats['years'][year] = stats['years'].get(year, 0) + 1
            
            # Count by publisher
            publisher = game.get('publisher')
            if publisher:
                stats['publishers'][publisher] = stats['publishers'].get(publisher, 0) + 1
            
            # Count by genre
            genre = game.get('genre')
            if genre:
                main_genre = genre.split(' - ')[0]
                stats['genres'][main_genre] = stats['genres'].get(main_genre, 0) + 1
            
            # Collect ratings
            rating = game.get('rating')
            if rating:
                stats['ratings'].append(rating)
        
        return stats
    
    def print_game(self, game: Dict):
        """Print a single game's information"""
        print(f"🎮 {game['title']} (ID: {game['id']})")
        print(f"   📅 Year: {game.get('year', 'N/A')}")
        print(f"   🏢 Publisher: {game.get('publisher', 'N/A')}")
        print(f"   🎯 Genre: {game.get('genre', 'N/A')}")
        print(f"   ⭐ Rating: {game.get('rating', 'N/A')}")
        print(f"   💬 Comments: {game.get('comment_count', 'N/A')}")
        print(f"   🖼️  Screenshot: {game.get('screenshot_url', 'N/A')}")
        print(f"   🔗 Detail: {game.get('detail_url', 'N/A')}")
        print()
    
    def print_statistics(self):
        """Print database statistics"""
        stats = self.get_statistics()
        
        print("📊 Database Statistics:")
        print(f"   Total games: {stats['total_games']}")
        
        if stats['years']:
            years = sorted(stats['years'].keys())
            print(f"   Year range: {min(years)} - {max(years)}")
            most_common_year = max(stats['years'], key=stats['years'].get)
            print(f"   Most common year: {most_common_year} ({stats['years'][most_common_year]} games)")
        
        if stats['publishers']:
            top_publishers = sorted(stats['publishers'].items(), key=lambda x: x[1], reverse=True)[:5]
            print("   Top publishers:")
            for publisher, count in top_publishers:
                print(f"     {publisher}: {count} games")
        
        if stats['genres']:
            top_genres = sorted(stats['genres'].items(), key=lambda x: x[1], reverse=True)[:5]
            print("   Top genres:")
            for genre, count in top_genres:
                print(f"     {genre}: {count} games")
        
        if stats['ratings']:
            avg_rating = sum(stats['ratings']) / len(stats['ratings'])
            print(f"   Average rating: {avg_rating:.2f}")
    
    def interactive_mode(self):
        """Run interactive search mode"""
        print("\n🔍 Interactive Search Mode")
        print("Commands: search <query>, year <year>, publisher <name>, stats, quit")
        
        while True:
            try:
                command = input("\n> ").strip().lower()
                
                if command == 'quit' or command == 'exit':
                    break
                elif command == 'stats':
                    self.print_statistics()
                elif command.startswith('search '):
                    query = command[7:].strip()
                    if query:
                        results = self.search_games(query)
                        print(f"Found {len(results)} games matching '{query}':")
                        for game in results[:10]:  # Show first 10 results
                            self.print_game(game)
                        if len(results) > 10:
                            print(f"... and {len(results) - 10} more")
                elif command.startswith('year '):
                    try:
                        year = int(command[5:].strip())
                        results = self.filter_by_year(year)
                        print(f"Found {len(results)} games from {year}:")
                        for game in results[:10]:
                            self.print_game(game)
                        if len(results) > 10:
                            print(f"... and {len(results) - 10} more")
                    except ValueError:
                        print("Invalid year format")
                elif command.startswith('publisher '):
                    publisher = command[10:].strip()
                    if publisher:
                        results = self.filter_by_publisher(publisher)
                        print(f"Found {len(results)} games by '{publisher}':")
                        for game in results[:10]:
                            self.print_game(game)
                        if len(results) > 10:
                            print(f"... and {len(results) - 10} more")
                else:
                    print("Unknown command. Try: search, year, publisher, stats, quit")
            
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")

def main():
    if len(sys.argv) > 1:
        db_file = sys.argv[1]
    else:
        db_file = "lemon64db.json"
    
    viewer = Lemon64Viewer(db_file)
    
    if len(sys.argv) > 2:
        # Command line search
        query = ' '.join(sys.argv[2:])
        results = viewer.search_games(query)
        print(f"Found {len(results)} games matching '{query}':")
        for game in results:
            viewer.print_game(game)
    else:
        # Interactive mode
        viewer.print_statistics()
        viewer.interactive_mode()

if __name__ == "__main__":
    main()
