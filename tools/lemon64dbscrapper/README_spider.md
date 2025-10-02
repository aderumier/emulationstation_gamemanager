# Lemon64 Web Spider

A Python web spider that scrapes game data from the Lemon64 database (https://www.lemon64.com/games/list.php) and creates a JSON database.

## Features

- 🕷️ **Systematic crawling**: Automatically discovers and follows pagination
- 🌐 **Realistic browser simulation**: Uses rotating user agents and comprehensive browser headers
- ⏱️ **Precise rate limiting**: Exactly 2 pages per second (0.5s delay) with user agent rotation
- 🎮 **Complete data extraction**: Game ID, title, year, publisher, genre, rating, screenshots, etc.
- 💾 **Continuous JSON saving**: Saves database after each individual game is processed
- 🔄 **Resume capability**: Can resume from existing database and progress tracking
- 📊 **Progress tracking**: Tracks page offset, game count, and session status
- 🧪 **Test mode**: Test with limited pages
- 🛡️ **Anti-detection**: User agent rotation and realistic browsing patterns

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements_spider.txt
```

## Usage

### Basic Usage
```bash
# Run the spider (collects all games)
python3 run_full_spider.py

# Test with limited pages
python3 test_spider.py
```

### Progress Tracking & Resume
```bash
# Check current status
python3 resume_spider.py status

# Resume from where you left off
python3 resume_spider.py resume

# Start completely fresh
python3 resume_spider.py fresh

# Test with limited pages
python3 resume_spider.py test --max-pages=5
```

### Legacy Usage
```bash
# Direct spider usage
python lemon64_spider.py

# Resume from existing database
python lemon64_spider.py --resume

# Limit number of pages (for testing)
python lemon64_spider.py --max-pages=5
```

## Output

The spider creates a `lemon64db.json` file with the following structure:

```json
{
  "6283": {
    "id": 6283,
    "title": "007 Car Chase",
    "year": 1985,
    "publisher": "Coplin Software",
    "genre": "Racing - Cars",
    "rating": 4.2,
    "comment_count": 2,
    "screenshot_url": "https://www.lemon64.com/assets/images/games/screens/007_car_chase/007_car_chase.png",
    "detail_url": "https://www.lemon64.com/game/007-car-chase"
  }
}
```

## Data Fields

- **id**: Unique game identifier
- **title**: Game title
- **year**: Release year
- **publisher**: Publisher/developer
- **genre**: Game genre and sub-genre
- **rating**: User rating (1-5 stars)
- **comment_count**: Number of user comments
- **screenshot_url**: URL to game screenshot
- **detail_url**: URL to detailed game page

## Browser Simulation & Rate Limiting

The spider simulates a real browser by:
- **Rotating User Agents**: Uses 12 different realistic browser user agents (Chrome, Firefox, Safari, Edge)
- **Comprehensive Headers**: Includes Accept, Accept-Language, DNT, Sec-Fetch-* headers
- **Fixed Rate**: Waits exactly 0.5 seconds between requests (2 pages per second)
- **Referer Headers**: Sets appropriate referer headers for pagination
- **Error Handling**: Graceful handling of timeouts, connection errors, and HTTP errors
- **Continuous Saving**: Database is saved after each individual game is processed, ensuring no data loss

## Error Handling

- Continues on individual game extraction errors
- Retries failed page requests
- Saves progress incrementally
- Graceful handling of network issues

## Example Output

```
🕷️  Starting Lemon64 spider with realistic browser simulation...
🌐 Using randomized user agents and realistic headers
⏱️  Rate limiting: 2 pages per second (0.5s delay)
🌐 Using User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...
📄 Fetching page with offset 0...
✅ Successfully loaded page (Status: 200)
🎮 Found 20 game cards on this page
✅ Extracted: 007 Car Chase (ID: 6283)
✅ Extracted: 10th Frame (ID: 6284)
...
📊 Total games collected so far: 20
🔄 Rotated to new User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...
⏳ Waiting 0.5 seconds before next page...
...
🎉 Spider completed! Collected 1500 games from 75 pages
💾 Database saved to lemon64db.json

📈 Database Statistics:
   Total games: 1500
   Year range: 1982 - 1994
   Most common year: 1985 (234 games)
   Top publisher: Ocean Software (89 games)
```
