# PlayStation Store Web Scraper

A Python web scraper that scrapes game data from the PlayStation Store website (https://store.playstation.com/en-ca/pages/browse/) and creates a JSON database.

## Features

- 🕷️ **Systematic crawling**: Automatically processes all game list pages (dynamically detects max page)
- 🌐 **Realistic browser simulation**: Uses rotating user agents and browser headers
- ⏱️ **Rate limiting**: Respectful delays between requests
- 🎮 **Complete data extraction**: Game name, publisher, release date, rating, number of players, description, boxfront, fanart
- 💾 **Continuous JSON saving**: Saves database after each individual game is processed
- 🔄 **Resume capability**: Can resume from existing database and progress tracking
- 📊 **Progress tracking**: Tracks current page, max page, and processed games
- 🔍 **Dynamic page detection**: Automatically detects maximum page number

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

- **`playstation_store_db.json`**: The main database file containing all scraped game data
- **`scraper_progress.json`**: Progress tracking file (used for resume functionality)

### Data Structure

Each game entry in the JSON database contains:

```json
{
  "231761": {
    "url": "https://store.playstation.com/en-ca/concept/231761",
    "name": "Diablo® IV",
    "publisher": "Blizzard Entertainment, Inc.",
    "release_date": "06-09-2024",
    "rating": 0.746,
    "nbplayers": "1-2",
    "boxfront": "https://image.api.playstation.com/vulcan/ap/rnd/202512/0923/4c56e76c73b8ffd76ab14074565ecd3e2d3848a70ece9c26.png",
    "fanart": "https://image.api.playstation.com/vulcan/ap/rnd/202405/3123/4168ef9b8695981a2e53f4a548319c27a32e320535a938ec.jpg",
    "description": "Diablo® IV - Standard Edition includes:\n\n- Diablo® IV for PS4® / PS5®\n\nDiablo® IV is the next-gen action RPG experience..."
  }
}
```

### Field Descriptions

- **`url`**: Full URL to the game's detail page
- **`name`**: Game name
- **`publisher`**: Publisher name (extracted from game page)
- **`release_date`**: Release date in dd-mm-yyyy format
- **`rating`**: Player rating normalized to 0-1 scale (original is 0-5, returns None if negative)
- **`nbplayers`**: Number of players (e.g., "1-2", "1")
- **`boxfront`**: URL to the boxfront image (query parameters removed)
- **`fanart`**: URL to the fanart/hero image (query parameters removed)
- **`description`**: Game description extracted from overview section (HTML converted to plain text with preserved line breaks)

## Resume Functionality

The scraper automatically saves progress after each game. If interrupted (Ctrl+C), you can resume by running:

```bash
python scrapper.py --resume
```

The scraper will:
- Load existing database entries
- Skip games that have already been processed
- Continue from the last page number
- Use the previously detected max page (or re-detect if starting fresh)

## How It Works

1. **Browse Pages**: The scraper fetches browse pages from `/en-ca/pages/browse/{page_number}`
2. **Max Page Detection**: On first run, automatically detects the maximum page number by checking pagination or trying pages incrementally
3. **Game Cards**: Each browse page contains game cards in `<li>` elements, from which basic info is extracted:
   - Game name
   - Game ID (from concept URL)
   - Boxfront image URL
4. **Game Details**: For each game, the scraper fetches the detail page using the concept URL
5. **HTML Parsing**: The detail page is parsed to extract:
   - Fanart (from hero image)
   - Rating (from screen reader text, normalized to 0-1)
   - Publisher (from multiple possible locations)
   - Number of players (from compatibility notices)
   - Release date (normalized to dd-mm-yyyy format)
   - Description (from overview section, HTML converted to text with preserved line breaks)
6. **Data Normalization**:
   - Release dates are converted from "9/6/2024" to "06-09-2024"
   - Ratings are normalized from 0-5 scale to 0-1 scale (None if negative)
   - Image URLs have query parameters removed
7. **Database Storage**: Each game is stored with its `id` as the key

## Notes

- The scraper uses realistic browser headers and rotates user agents to avoid detection
- Rate limiting is implemented with delays between requests (1 second between games, 2 seconds between pages)
- Image URLs are automatically cleaned by removing query parameters (`?w=...&thumb=...`)
- The description field preserves line breaks from the original HTML
- Max page detection happens automatically on first run or when starting fresh

