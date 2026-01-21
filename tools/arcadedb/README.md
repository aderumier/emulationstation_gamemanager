# ArcadeDB Scraper

A Python scraper that extracts game data from ArcadeItalia API by parsing .dat XML files and creates a JSON database.

## Features

- 📁 **XML Parsing**: Automatically processes all .dat XML files in the directory to extract machine names
- 🌐 **Batch API Integration**: Queries ArcadeItalia API in batches of up to 800 games per request for optimal performance
- 🌐 **Realistic browser simulation**: Uses rotating user agents and browser headers
- ⏱️ **Rate limiting**: Respectful delays between API requests
- 🎮 **Complete data extraction**: Game ID, name, genre, release date, publisher, players, rating, description, images, YouTube videos
- 💾 **Continuous JSON saving**: Saves database after each batch is processed
- 🔄 **Resume capability**: Can resume from existing database and progress tracking
- 📊 **Progress tracking**: Tracks processed games and files

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Place .dat XML files in the `tools/arcadedb/` directory

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

- **`arcadedb_db.json`**: The main database file containing all scraped game data
- **`scraper_progress.json`**: Progress tracking file (used for resume functionality)

### Data Structure

Each game entry in the JSON database contains:

```json
{
  "005": {
    "id": "005",
    "name": "005",
    "genre": "Action",
    "release_date": "01-01-1981",
    "publisher": "Sega",
    "nbplayers": "1-2",
    "rating": 4.5,
    "description": "Game history and description...",
    "boxfront": "https://...",
    "titleshot": "https://...",
    "screenshot": "https://...",
    "cabinet": "https://...",
    "youtubeurl": "https://www.youtube.com/watch?v=..."
  }
}
```

### Field Descriptions

- **id**: Game ID (machine name from .dat file)
- **name**: Game name (from API "title" field)
- **genre**: Game genre (from API "genre" field)
- **release_date**: Release date in "01-01-YYYY" format (converted from API "year" field)
- **publisher**: Publisher/manufacturer name (from API "manufacturer" field)
- **nbplayers**: Number of players (from API "players" field)
- **rating**: Rating normalized to /5 scale (original is /100, divided by 20)
- **description**: Game history/description (from API "history" field)
- **boxfront**: URL to flyer/box art image (from API "url_image_flyer" field)
- **titleshot**: URL to title screen image (from API "url_image_title" field)
- **screenshot**: URL to in-game screenshot (from API "url_image_ingame" field)
- **cabinet**: URL to cabinet image (from API "url_image_cabinet" field)
- **youtubeurl**: YouTube video URL (constructed from API "youtube_video_id" field)

## Resume Functionality

The scraper automatically saves progress after each game. If interrupted (Ctrl+C), you can resume by running:

```bash
python scrapper.py --resume
```

The scraper will:
- Skip already processed games
- Skip already processed .dat files
- Maintain the database with all previously scraped games

## How It Works

1. **Parse .dat Files**: The scraper finds all `.dat` XML files in the `tools/arcadedb/` directory
2. **Extract Machine Names**: Parses XML to extract all `<machine>` elements with `name` attributes
3. **Batch API Queries**: Groups games into batches of up to 800 and queries `http://adb.arcadeitalia.net/service_scraper.php?ajax=query_mame&game_name=<id1>;<id2>;...;<id800>` for optimal performance
4. **Extract Data**: Extracts and normalizes game information from the API response for each game in the batch
5. **Save Progress**: Saves both the database and progress after each batch

## Notes

- The scraper processes all .dat files found in the directory
- Games are processed in batches of up to 800 for optimal API performance
- Games are saved after each batch is processed
- Rate limiting is built-in (1 second between batches) to be respectful to the server
- The script can be stopped and resumed at any time
- Games with no API data are skipped (not added to database)
- Rating is normalized from /100 to /5 scale by dividing by 20
- Year is converted to "01-01-YYYY" format for consistency
- Batch processing significantly reduces the number of API calls and improves scraping speed
