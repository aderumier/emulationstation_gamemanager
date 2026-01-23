# Hall of Light (HOL) Web Scraper

A Python web scraper that scrapes game data from the Hall of Light Amiga database (https://amiga.abime.net/games/list/) and creates a JSON database.

## Features

- 🕷️ **Systematic crawling**: Automatically processes all games from page 1 to 227 (grid view)
- 🎮 **Multiple versions**: Handles games with multiple versions (ECS/OCS, AGA, CD32, CDTV, etc.)
- 🌐 **Realistic browser simulation**: Uses rotating user agents and browser headers
- ⏱️ **Rate limiting**: Respectful delays between requests
- 🎮 **Complete data extraction**: Game ID, name, developer, publisher, release date, description, screenshots
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
# Run the scraper (uses Selenium by default to bypass bot protection)
python scrapper.py

# Start fresh (clears progress)
python scrapper.py --fresh

# Resume from last position
python scrapper.py --resume

# Check current status
python scrapper.py --status

# Disable Selenium (not recommended - site has bot protection)
python scrapper.py --no-selenium
```

**Note:** This site uses Anubis bot protection which requires JavaScript execution. Selenium is enabled by default to handle this. Make sure you have ChromeDriver installed.

### Output Files

- **`hol_db.json`**: The main database file containing all scraped game data
- **`scraper_progress.json`**: Progress tracking file (used for resume functionality)

### Data Structure

Each game version entry in the JSON database contains:

```json
{
  "body-blows-ecs-ocs": {
    "url": "https://amiga.abime.net/games/view/body-blows",
    "gameid": "body-blows-ecs-ocs",
    "name": "Body Blows (ECS / OCS)",
    "developer": "Unknown",
    "genre": null,
    "release_date": "01-01-1993",
    "publisher": "Team 17",
    "description": "Notes: \"Dance\" music by Allister Brimble...",
    "titleshot": "https://amiga.abime.net/screen/0101-0200/171_screen0.png?v=335",
    "screenshot": "https://amiga.abime.net/screen/0101-0200/171_screen1.png?v=336"
  },
  "body-blows-aga": {
    "url": "https://amiga.abime.net/games/view/body-blows",
    "gameid": "body-blows-aga",
    "name": "Body Blows (AGA)",
    "developer": null,
    "genre": null,
    "release_date": "01-01-1994",
    "publisher": "Team 17",
    "description": null,
    "titleshot": "https://amiga.abime.net/screen/0101-0200/172_screen0.png?v=337",
    "screenshot": "https://amiga.abime.net/screen/0101-0200/172_screen1.png?v=338"
  },
  "body-blows-cd32": {
    "url": "https://amiga.abime.net/games/view/body-blows",
    "gameid": "body-blows-cd32",
    "name": "Body Blows (CD32)",
    "developer": "Team 17",
    "genre": null,
    "release_date": "01-01-1994",
    "publisher": "Team 17",
    "description": "Game features CDDA music tracks...",
    "titleshot": "https://amiga.abime.net/screen/1701-1800/1797_screen0.png?v=3563",
    "screenshot": "https://amiga.abime.net/screen/1701-1800/1797_screen1.png?v=3564"
  }
}
```

### Version Handling

Games on HOL can have multiple versions for different Amiga hardware:

- **ECS / OCS**: Original Amiga chipset
- **AGA**: Advanced Graphics Architecture (A1200, A4000)
- **CD32**: Amiga CD32 console
- **CDTV**: Commodore CDTV
- And others...

For games with **multiple versions**, each version is stored as a separate entry:
- `gameid`: `<base-id>-<version-slug>` (e.g., `body-blows-ecs-ocs`)
- `name`: `<Game Name> (<Version>)` (e.g., `Body Blows (ECS / OCS)`)

For games with a **single version**, the original gameid and name are preserved:
- `gameid`: `turrican`
- `name`: `Turrican`

### Field Descriptions

- **url**: Full URL to the game detail page
- **gameid**: Unique game ID (includes version suffix for multi-version games)
- **name**: Game name (includes version in parentheses for multi-version games)
- **developer**: Developer name (from version info)
- **genre**: Genre (if available)
- **release_date**: Release date in "01-01-YYYY" format (from first release in version)
- **publisher**: Publisher name (from first release in version)
- **description**: Notes/description text (from version block)
- **titleshot**: URL to title screen image (matched by version from carousel)
- **screenshot**: URL to gameplay screenshot (matched by version from carousel)

## Resume Functionality

The scraper automatically saves progress after each game. If interrupted (Ctrl+C), you can resume by running:

```bash
python scrapper.py --resume
```

The scraper will:
- Skip already processed game URLs
- Continue from the last page it was processing
- Maintain the database with all previously scraped entries

## Notes

- The scraper processes games by page number (1-227 in grid view)
- Each page contains multiple games
- Games with multiple versions create multiple database entries
- Games are saved immediately after being scraped
- Rate limiting is built-in to be respectful to the server
- The script can be stopped and resumed at any time
- Images are matched to versions by parsing the `data-title` attribute (e.g., "ECS no. 1" for titleshot)

## Source Website

- **Hall of Light (HOL)**: https://amiga.abime.net/
- **Games List (Grid View)**: https://amiga.abime.net/games/list/?view=grid&page=1
