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

# Check progress
python tools/igdb/progress.py show

# Clear progress (start fresh)
python tools/igdb/progress.py clear
```

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
- **`covers.json`** - Game cover images
- **`screenshots.json`** - Game screenshots
- **`artworks.json`** - Game artworks
- **`dump_summary.json`** - Summary with statistics and metadata

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
