# Myrient Directory Scraper

A Python web scraper that scrapes directory listings from Myrient's Redump and No-Intro file repositories and creates JSON database files indexed by filename.

## Features

- 🕷️ **Systematic crawling**: Automatically processes all directories recursively from Redump and No-Intro
- 🌐 **Realistic browser simulation**: Uses rotating user agents and browser headers
- ⏱️ **Rate limiting**: Respectful delays between requests
- 📁 **Directory grouping**: Automatically groups directories with same base name (removing `(Aftermarket)` and `(Private)` suffixes)
- 💾 **JSON databases**: Creates separate JSON files for each directory group, prefixed with `redump_` or `nointro_`
- 🔄 **Resume capability**: Can resume from existing progress tracking
- 📊 **Progress tracking**: Tracks processed directories and URLs

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

- **`{redump_|nointro_}{directory_name}.json`**: JSON database files for each directory group, one file per group
- **`scraper_progress.json`**: Progress tracking file (used for resume functionality)

### Data Structure

Each JSON file contains file entries indexed by filename:

```json
{
  "filename1.zip": {
    "filename": "filename1.zip",
    "date": "18-Feb-2025 11:50",
    "size": "1234567890",
    "url": "https://myrient.erista.me/files/Redump/Nintendo - Gameboy/filename1.zip"
  },
  "filename2.zip": {
    "filename": "filename2.zip",
    "date": "19-Feb-2025 10:30",
    "size": "2345678901",
    "url": "https://myrient.erista.me/files/Redump/Nintendo - Gameboy (Aftermarket)/filename2.zip"
  }
}
```

## Directory Grouping

The scraper automatically groups directories that share the same base name:

- `Nintendo - Gameboy`
- `Nintendo - Gameboy (Aftermarket)`
- `Nintendo - Gameboy (Private)`

All files from these directories are merged into a single JSON file: `redump_Nintendo - Gameboy.json` or `nointro_Nintendo - Gameboy.json`

## Resume Functionality

The scraper automatically saves progress after each directory. If interrupted (Ctrl+C), you can resume by running:

```bash
python scrapper.py --resume
```

The scraper will:
- Skip already processed directories
- Continue from the last source it was processing (Redump or No-Intro)
- Maintain all previously created JSON files

## Sources

- **Redump**: `https://myrient.erista.me/files/Redump/`
- **No-Intro**: `https://myrient.erista.me/files/No-Intro/`

## Notes

- The scraper processes Redump first, then No-Intro
- Files from grouped directories (with `(Aftermarket)` or `(Private)` variants) are merged into the base directory's JSON file
- JSON filenames are sanitized to remove filesystem-unsafe characters
- Rate limiting is built-in to be respectful to the server
- The script can be stopped and resumed at any time



