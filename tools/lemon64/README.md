# Lemon64 Web Scraper

A Python web scraper that scrapes game data from the Lemon64 website (https://www.lemon64.com/games/list.php) and creates a JSON database.

## Features

- 🕷️ **Systematic crawling**: Automatically processes all games from offset 0 to 5000 (incrementing by 40)
- 🌐 **Realistic browser simulation**: Uses rotating user agents and browser headers
- ⏱️ **Rate limiting**: Respectful delays between requests
- 🎮 **Complete data extraction**: Game ID, name, developer, publisher, genre, release date, rating, votes, box scans, screenshots, YouTube videos
- 💾 **Continuous JSON saving**: Saves database after each individual game is processed
- 🔄 **Resume capability**: Can resume from existing database and progress tracking
- 📊 **Progress tracking**: Tracks current offset and processed games

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
# Run the scraper (resumes from last position if available)
python scrapper.py

# Start fresh (clears progress)
python scrapper.py --fresh

# Resume from last position
python scrapper.py --resume

# Check current status
python scrapper.py --status
```

### Output Files

- **`lemon64_db.json`**: The main database file containing all scraped game data
- **`scraper_progress.json`**: Progress tracking file (used for resume functionality)

### Data Structure

Each game entry in the JSON database contains:

```json
{
  "game-slug": {
    "url": "https://www.lemon64.com/game/game-slug",
    "gameid": 1366,
    "name": "Game Name",
    "developer": "Developer Name",
    "genre": "Genre",
    "release_date": "01-01-1989",
    "publisher": "Publisher Name",
    "rating": 3.815,
    "nbvote": 8,
    "boxfront": "https://www.lemon64.com/uploads/images/games/covers/large/game_01.jpg",
    "boxback": "https://www.lemon64.com/uploads/images/games/covers/large/game_02.jpg",
    "titleshot": "https://www.lemon64.com/assets/images/games/screens/game/game_01.png",
    "screenshot": "https://www.lemon64.com/assets/images/games/screens/game/game_02.png",
    "youtubeurl": "https://www.youtube.com/watch?v=VIDEO_ID"
  }
}
```

### Field Descriptions

- **url**: Full URL to the game detail page
- **gameid**: Unique game ID from Lemon64
- **name**: Game name
- **developer**: Developer name
- **genre**: Main genre (extracted from category, e.g., "Arcade" from "Arcade - Miscellaneous")
- **release_date**: Release date in "01-01-YYYY" format
- **publisher**: Publisher name
- **rating**: Rating normalized to /5 scale (original is /10, divided by 2)
- **nbvote**: Number of votes
- **boxfront**: URL to front cover scan image
- **boxback**: URL to back cover scan image
- **titleshot**: URL to first screenshot (title screen)
- **screenshot**: URL to second screenshot (gameplay)
- **youtubeurl**: YouTube video URL (if available)

## Resume Functionality

The scraper automatically saves progress after each game. If interrupted (Ctrl+C), you can resume by running:

```bash
python scrapper.py --resume
```

The scraper will:
- Skip already processed games
- Continue from the last offset it was processing
- Maintain the database with all previously scraped games

## Notes

- The scraper processes games by pagination offset (0, 40, 80, ..., 5000)
- Each offset page may contain up to 40 games
- Games are saved immediately after being scraped
- Rate limiting is built-in to be respectful to the server
- The script can be stopped and resumed at any time
- Rating is parsed from image filenames and normalized from /10 to /5 scale
