# Atari Legend Web Scraper

A Python web scraper that scrapes game data from the Atari Legend website (https://www.atarilegend.com/games) and creates a JSON database.

## Features

- 🕷️ **Systematic crawling**: Automatically processes all games from A-Z and 0-9
- 🌐 **Realistic browser simulation**: Uses rotating user agents and browser headers
- ⏱️ **Rate limiting**: Respectful delays between requests
- 🎮 **Complete data extraction**: Developer, genre, release date, box scans, screenshots
- 💾 **Continuous JSON saving**: Saves database after each individual game is processed
- 🔄 **Resume capability**: Can resume from existing database and progress tracking
- 📊 **Progress tracking**: Tracks current letter, page, and processed games

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

- **`atarilegend_db.json`**: The main database file containing all scraped game data
- **`scraper_progress.json`**: Progress tracking file (used for resume functionality)

### Data Structure

Each game entry in the JSON database contains:

```json
{
  "game-slug": {
    "url": "https://www.atarilegend.com/games/game-slug",
    "developer": "Developer Name",
    "genre": "Genre Name",
    "release_date": "1989",
    "boxfront": "https://www.atarilegend.com/storage/images/game_release_scans/3381.jpg",
    "boxback": "https://www.atarilegend.com/storage/images/game_release_scans/3382.jpg",
    "titleshot": "https://www.atarilegend.com/games/game-slug/screenshot-3577.png",
    "screenshot": "https://www.atarilegend.com/games/game-slug/screenshot-3578.png"
  }
}
```

## Resume Functionality

The scraper automatically saves progress after each game. If interrupted (Ctrl+C), you can resume by running:

```bash
python scrapper.py --resume
```

The scraper will:
- Skip already processed games
- Continue from the last letter/page it was processing
- Maintain the database with all previously scraped games

## Notes

- The scraper processes games alphabetically (A-Z and 0-9)
- Each letter may have multiple pages of results
- Games are saved immediately after being scraped
- Rate limiting is built-in to be respectful to the server
- The script can be stopped and resumed at any time

