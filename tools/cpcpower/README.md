# CPC Power Web Scraper

A Python web scraper that scrapes game data from the CPC Power website (https://www.cpc-power.com/index.php?page=database) and creates a JSON database.

## Features

- 🕷️ **Systematic crawling**: Automatically processes all game list pages (position 1 to 993)
- 🌐 **Realistic browser simulation**: Uses rotating user agents and browser headers
- ⏱️ **Rate limiting**: Respectful delays between requests
- 🎮 **Complete data extraction**: Game name, year, publisher, genre, number of players, description, tricks, screenshots, map, manual
- 💾 **Continuous JSON saving**: Saves database after each individual game is processed
- 🔄 **Resume capability**: Can resume from existing database and progress tracking
- 📊 **Progress tracking**: Tracks current position and processed games
- 🖼️ **Image validation**: Checks for map and manual URLs using HEAD requests

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

- **`cpcpower_db.json`**: The main database file containing all scraped game data
- **`scraper_progress.json`**: Progress tracking file (used for resume functionality)

### Data Structure

Each game entry in the JSON database contains:

```json
{
  "482": {
    "url": "https://www.cpc-power.com/index.php?page=detail&num=482",
    "game_id": "482",
    "name": "Game Name",
    "year": "01-01-1984",
    "publisher": "Publisher Name",
    "genre": "Fight",
    "nbplayer": 1,
    "description": "Game description text...",
    "tricks": "<p>HTML content with tricks...</p>",
    "titleshot": "https://www.cpc-power.com/extra_lire_fichier.php?extra=cpcold&fiche=482&slot=1&part=A&type=.png",
    "screenshot": "https://www.cpc-power.com/extra_lire_fichier.php?extra=cpcold&fiche=482&slot=2&part=A&type=.png",
    "map": "https://www.cpc-power.com/extra_lire_fichier.php?extra=plan&fiche=482&slot=1&part=A&type=.png",
    "manual": "https://www.cpc-power.com/extra_lire_fichier.php?extra=notice&fiche=482&slot=1&part=A&type=.jpg"
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
- Continue from the last position it was processing
- Maintain the database with all previously scraped games

## Data Extraction Details

### From List Pages
- **Game ID**: Extracted from `num` parameter in the detail page link
- **Game Name**: Extracted from the link text within `<div class="listingcarttitre">`
- **Year**: Extracted from `<h2 class="listebdd">` (format: "01-01-YYYY")
- **Publisher**: Extracted from `<h2 class="listebdd">` (after © character)
- **Titleshot**: Extracted from the first image in the listing block

### From Detail Pages
- **Genre**: First genre from the categories section (removes leading arrows)
- **Number of Players**: Integer extracted from the first line of the players section
- **Description**: Text content with HTML entity encoding
- **Tricks**: Full HTML content with HTML entity encoding
- **Screenshot**: Second image from the carousel (`div.mondiaporama`)
- **Map**: URL checked via HEAD request (only included if exists)
- **Manual**: URL checked via HEAD request (only included if exists)

## Notes

- The scraper processes game list pages from position 1 to 993
- Each position may contain multiple games
- Games are saved immediately after being scraped
- Rate limiting is built-in to be respectful to the server
- The script can be stopped and resumed at any time
- HTML entities are properly encoded in description and tricks fields



