# Adventure Game Studio Web Scraper

A Python web scraper that scrapes game data from the Adventure Game Studio website (https://www.adventuregamestudio.co.uk/play/search/) and creates a JSON database.

## Features

- 🕷️ **Systematic crawling**: Automatically processes all game list pages (page 1 to 51)
- 🌐 **Realistic browser simulation**: Uses rotating user agents and browser headers
- ⏱️ **Rate limiting**: Respectful delays between requests
- 🎮 **Complete data extraction**: Game name, developer, release date, rating, description, titleshot, screenshot
- 💾 **Continuous JSON saving**: Saves database after each individual game is processed
- 🔄 **Resume capability**: Can resume from existing database and progress tracking
- 📊 **Progress tracking**: Tracks current page and processed games

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

- **`ags_db.json`**: The main database file containing all scraped game data
- **`scraper_progress.json`**: Progress tracking file (used for resume functionality)

### Data Structure

Each game entry in the JSON database contains:

```json
{
  "2835": {
    "url": "https://www.adventuregamestudio.co.uk/play/game/2883-metro-city-resistance",
    "name": "Bathroom Adventure",
    "developer": "Developer Name",
    "release_date": "21-03-2025",
    "rating": 0.8,
    "titleshot": "https://www.adventuregamestudio.co.uk/site/assets/img/games/2864_1.webp",
    "screenshot": "https://www.adventuregamestudio.co.uk/site/assets/img/games/2864_2.webp",
    "description": "Game description text with line breaks..."
  }
}
```

### Field Descriptions

- **`url`**: Full URL to the game's detail page
- **`name`**: Game name
- **`developer`**: Developer name (extracted from game page)
- **`release_date`**: Release date in dd-mm-yyyy format
- **`rating`**: Player rating normalized to 0-1 scale (original is 0-5)
- **`titleshot`**: URL to the first image (titleshot) from the gallery
- **`screenshot`**: URL to the second image (screenshot) from the gallery
- **`description`**: Game description extracted from the "About" section (HTML converted to plain text)

## Resume Functionality

The scraper automatically saves progress after each game. If interrupted (Ctrl+C), you can resume by running:

```bash
python scrapper.py --resume
```

The scraper will:
- Load existing database entries
- Skip games that have already been processed
- Continue from the last page number

## How It Works

1. **Search Endpoint**: The scraper POSTs to the search endpoint with pagination (pages 1-51)
2. **Game List**: Each page returns a JSON list of games with basic information (id, name, release_date, rating, pretty_game_url)
3. **Game Details**: For each game, the scraper fetches the detail page using the `pretty_game_url`
4. **HTML Parsing**: The detail page is parsed to extract:
   - Developer name (from the h2 heading after "by")
   - Images (from the gallery's data-dynamicel attribute - first image is titleshot, second is screenshot)
   - Description (from the "About" section, with HTML converted to plain text)
5. **Data Normalization**:
   - Release dates are converted from "2025-03-21 04:02:55" to "21-03-2025"
   - Ratings are normalized from 0-5 scale to 0-1 scale (divided by 5)
6. **Database Storage**: Each game is stored with its `id` as the key

## Notes

- The scraper uses realistic browser headers and rotates user agents to avoid detection
- Rate limiting is implemented with delays between requests (1 second between games, 2 seconds between pages)
- Image URLs are automatically converted to absolute URLs if they are relative
- The description field preserves line breaks from the original HTML

