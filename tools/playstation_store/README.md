# PlayStation Store Web Scraper

A Python web scraper that scrapes game data from the PlayStation Store website (https://store.playstation.com/en-ca/pages/browse/) and creates a JSON database.

## Features

- 🕷️ **Systematic crawling**: Walks the whole "All Games" catalogue through the store's own GraphQL API
- 🌐 **Realistic browser simulation**: Uses rotating user agents and browser headers
- ⏱️ **Rate limiting**: Respectful delays plus exponential backoff on errors
- 🎮 **Complete data extraction**: Game name, publisher, release date, rating, number of players, description, boxfront, fanart
- 💾 **Crash-safe saving**: Writes atomically so an interrupted run can't truncate the database
- 🔄 **Resume capability**: Can resume from existing database and progress tracking
- 📊 **Progress tracking**: Tracks catalogue offset and processed games
- 🔍 **Dynamic category detection**: Resolves the "All Games" category id at runtime

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

# Restart the catalogue walk from the beginning
# (keeps the database and skips games already in it)
python scrapper.py --fresh

# Resume from last position
python scrapper.py --resume

# Check current status
python scrapper.py --status
```

### Options

| Option | Default | Description |
| --- | --- | --- |
| `--locale` | `en-ca` | Store locale to scrape |
| `--page-size` | `100` | Games fetched per catalogue call (max 500) |
| `--save-every` | `25` | Write the database after this many new games |
| `--delay` | `1.0` | Base delay in seconds between game detail pages |

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
    "rating": 0.75,
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

The scraper saves progress periodically (every `--save-every` games and after each catalogue page). If interrupted (Ctrl+C), you can resume by running:

```bash
python scrapper.py --resume
```

The scraper will:
- Load existing database entries
- Skip games that are already in the database (no detail request is made for them)
- Continue from the last catalogue offset

Data files are always read from and written to the directory containing `scrapper.py`, so the scraper can be run from any working directory.

## How It Works

1. **Catalogue Listing**: The `/pages/browse/` HTML is rendered client-side and contains no games, so the listing is read from the same GraphQL endpoint the website calls (`categoryGridRetrieve` on `web.np.playstation.com`). Each call returns a page of "concepts":
   - Game name
   - Game ID
   - Boxfront image URL (the `MASTER` media role)
2. **Category Detection**: The "All Games" category id is resolved at runtime from the Browse experience, falling back to a known id
3. **Game Details**: For each game not already in the database, the scraper fetches the detail page at `/{locale}/concept/{id}`, which is still server-rendered
4. **HTML Parsing**: The detail page is parsed to extract:
   - Fanart (from hero image)
   - Rating (from screen reader text, normalized to 0-1)
   - Publisher (from multiple possible locations)
   - Number of players (from compatibility notices)
   - Release date (normalized to dd-mm-yyyy format)
   - Description (from overview section, HTML converted to text with preserved line breaks)
5. **Data Normalization**:
   - Release dates are converted from "9/6/2024" to "06-09-2024"
   - Ratings are normalized from 0-5 scale to 0-1 scale (None if negative)
   - Image URLs have query parameters removed
6. **Database Storage**: Each game is stored with its `id` as the key

## Notes

- The scraper uses realistic browser headers and rotates user agents to avoid detection
- Rate limiting is implemented with delays between requests, plus exponential backoff on 429/5xx responses
- Image URLs are automatically cleaned by removing query parameters (`?w=...&thumb=...`)
- The description field preserves line breaks from the original HTML

### Catalogue depth limit

The store reports ~10,000 games in the "All Games" category and refuses any request past
`offset + size > 10000`, so a full walk yields roughly 10k titles. Reaching anything beyond
that requires narrowing the query with facet filters (by genre, platform, release date, …).

### If the listing stops working again

The GraphQL endpoint only accepts *persisted queries*: operations are referenced by the
SHA-256 hash of the document the web client sends, and freeform queries are rejected. Those
hashes live in `PERSISTED_QUERIES` at the top of `scrapper.py`. If PlayStation changes them,
the scraper reports that the stored hash is no longer accepted; re-capture it by loading
`https://store.playstation.com/en-ca/pages/browse/1` in a browser with devtools open and
reading the `extensions` query parameter of the `categoryGridRetrieve` request.

