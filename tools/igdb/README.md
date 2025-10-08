# IGDB Database Dump Tool

This tool allows you to dump data from the IGDB (Internet Game Database) API into local JSON files for offline analysis and reference.

## Features

- **Standalone Tool**: Completely independent of the main application
- **Comprehensive Data Dumping**: Dumps games, platforms, genres, companies, and media
- **Rate Limiting**: Built-in rate limiting to respect IGDB API limits
- **Batch Processing**: Handles large datasets with pagination
- **Media Support**: Downloads covers and screenshots for games
- **Summary Generation**: Creates a summary file with statistics
- **Stop/Resume Support**: Can be stopped and resumed at any time
- **Progress Tracking**: Saves progress to resume from where it left off

## Prerequisites

1. **Python Dependencies**: Install required packages
   ```bash
   pip install -r tools/igdb/requirements.txt
   ```

2. **IGDB API Credentials**: You need a Twitch Client ID and Client Secret
   - Register at [Twitch Developer Portal](https://dev.twitch.tv/)
   - Create a new application to get your credentials

3. **Configuration**: Add your credentials to `var/config/credentials.json`:
   ```json
   {
     "igdb": {
       "client_id": "your_client_id_here",
       "client_secret": "your_client_secret_here"
     }
   }
   ```

## Usage

### Basic Usage

```bash
# Run the dump script
python tools/igdb/dump.py

# Force redump of all files (ignore existing files)
python tools/igdb/dump.py --force

# Check progress
python tools/igdb/progress.py show

# Clear progress (start fresh)
python tools/igdb/progress.py clear
```

### File-Based Skipping

By default, the dump script will skip files that already exist and contain valid data:

- **Skip existing files**: If a JSON file already exists and contains data, it will be loaded instead of redumping
- **Force redump**: Use `--force` flag to ignore existing files and redump everything
- **Validation**: Files are validated to ensure they contain valid JSON data before being skipped

### Stop/Resume Functionality

The dump script supports stopping and resuming:

1. **Stop the dump**: Press `Ctrl+C` at any time
2. **Resume the dump**: Simply run the script again - it will continue from where it left off
3. **Check progress**: Use `python tools/igdb/progress.py show` to see current status
4. **Start fresh**: Use `python tools/igdb/progress.py clear` to clear progress and start over

### What Gets Dumped

The script will create the following files in `var/db/igdb/dump/`:

- **`platforms.json`** - All gaming platforms (PC, PlayStation, Xbox, etc.)
- **`genres.json`** - Game genres (Action, RPG, Strategy, etc.)
- **`game_modes.json`** - Game modes (Single-player, Multiplayer, etc.)
- **`player_perspectives.json`** - Player perspectives (First-person, Third-person, etc.)
- **`companies.json`** - Game companies (developers, publishers)
- **`games.json`** - Complete game database (all games)
- **`all_covers.json`** - All cover images from IGDB database
- **`all_screenshots.json`** - All screenshots from IGDB database
- **`all_artworks.json`** - All artworks from IGDB database
- **`all_videos.json`** - All game videos from IGDB database
- **`all_alternative_names.json`** - All alternative names from IGDB database
- **`igdb.json`** - Consolidated games database with resolved media references
- **`igdb_db.pkl`** - Pickle version of consolidated games database for faster loading
- **`igdb_companies.pkl`** - Pickle version of companies lookup (id => name) for faster loading
- **`platform_partition_index.json`** - Platform-partitioned search index for efficient game lookup
- **`igdb_platform_partition_index.pkl`** - Pickle version of platform partition index for faster loading
- **`dump_summary.json`** - Summary with statistics and metadata

### Consolidated igdb.json

The script automatically creates a consolidated `var/db/igdb/igdb.json` file that:

- **Uses game ID as key**: `{game_id: game_data}` structure for efficient lookup
- **Removes unnecessary fields**: Excludes `similar_games`, `websites`, `age_ratings`, `external_games`, `url`, `player_perspectives`, `game_modes`, `game_engines`, `release_dates`, `alternative_names`, and `id` to reduce file size
- **Resolves media references**: 
  - `cover` integer ID → `image_id` from covers database
  - `screenshots` array of IDs → array of `image_id` from screenshots database
  - `artworks` array of IDs → array of `image_id` from artworks database
  - `videos` array of video objects → array of video data from videos database
- **Adds company information**:
  - `publisher` → company ID (single ID or array for multiple publishers)
  - `developer` → company ID (single ID or array for multiple developers)
- **Optimized for applications**: Ready-to-use format for game lookup and media display

### Platform Partition Index

The script automatically creates a platform-partitioned search index at `var/db/igdb/platform_partition_index.json` that:

- **Structure**: `[platform_id][first_letter][normalized_name] = game_id`
- **Includes all names**: Both main game names and alternative names from the database
- **Normalized search**: Uses the same normalization function as other services for consistent matching
- **Efficient lookup**: Partitioned by platform and first letter for fast searches
- **Complete coverage**: Every game name (main + alternatives) is indexed for each platform

#### Example structure:
```json
{
  "6": {  // PlayStation platform ID
    "s": {
      "supermariobros": 12345,
      "supermariobros3": 12346
    },
    "m": {
      "mariokart": 12347,
      "metroid": 12348
    }
  },
  "7": {  // Nintendo 64 platform ID
    "s": {
      "supermario64": 12349,
      "supermariobros": 12350
    }
  }
}
```

This index enables fast platform-specific game searches using normalized names, similar to the MobyGames and Launchbox partitioned indexes.

### Pickle Files for Performance

The script automatically generates pickle (`.pkl`) versions of the main data files for significantly faster loading:

- **`igdb_db.pkl`** - Binary version of the consolidated games database
- **`igdb_companies.pkl`** - Binary version of companies lookup (id => name mapping)
- **`igdb_platform_partition_index.pkl`** - Binary version of the platform partition index

#### Benefits of Pickle Files:
- **Faster loading**: 5-10x faster than JSON parsing for large datasets
- **Memory efficient**: Direct Python object deserialization
- **Production ready**: Ideal for applications that need to load data frequently
- **Same data**: Identical content to JSON files, just in binary format

#### Usage Example:
```python
import pickle

# Load consolidated games database
with open('var/db/igdb/igdb_db.pkl', 'rb') as f:
    igdb_data = pickle.load(f)

# Load companies lookup
with open('var/db/igdb/igdb_companies.pkl', 'rb') as f:
    companies = pickle.load(f)

# Load platform partition index
with open('var/db/igdb/igdb_platform_partition_index.pkl', 'rb') as f:
    platform_index = pickle.load(f)
```

### Customization

You can modify the script to:

1. **Change the game limit**: Edit the `max_games` parameter in the `main()` function
2. **Add more fields**: Modify the query strings in each dump method
3. **Change output directory**: Modify the `dump_dir` variable in the `IGDBDumper` class
4. **Adjust rate limiting**: Modify the `request_delay` variable

### Example: Limit Games (Optional)

```python
# If you want to limit the number of games (for testing), you can specify:
games = await dumper.dump_games(max_games=10000)  # Dump 10,000 games

# By default, it dumps ALL games from the IGDB database
games = await dumper.dump_games()  # Dump all games
```

## API Rate Limits

The IGDB API has rate limits:
- **4 requests per second** for most endpoints
- **8 requests per second** for some endpoints

The script includes built-in rate limiting (100ms delay between requests) to stay within these limits.

## Data Structure

### Games Data
Each game includes fields like:
- `id`, `name`, `slug`
- `summary`, `storyline`
- `first_release_date`
- `rating`, `total_rating`
- `genres`, `platforms`, `game_modes`
- `cover`, `screenshots`, `artworks`
- `websites`, `url`

### Media Data
- **Covers**: Game cover images with dimensions and URLs
- **Screenshots**: In-game screenshots with dimensions and URLs
- **Artworks**: Game artworks with dimensions and URLs

## Troubleshooting

### Common Issues

1. **Authentication Error**: Make sure your IGDB credentials are correctly set in `var/config/credentials.json`
2. **Rate Limit Exceeded**: The script has built-in rate limiting, but you can increase the delay if needed
3. **Memory Issues**: For large dumps, consider processing in smaller batches

### Debug Mode

Add debug logging by modifying the script:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Based On

This implementation is based on the GameCompendium project:
- [GameCompendium IGDB Implementation](https://github.com/SnowyCoder/gamecompendium/blob/main/gamecompendium/igdb.py)

## License

This tool is part of the CursorScraper project and follows the same license terms.
