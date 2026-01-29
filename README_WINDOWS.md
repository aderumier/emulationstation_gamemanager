# GameManager for Windows

This document provides information about the Windows executable version of GameManager.

## Overview

The Windows executable is a standalone version of GameManager that includes all Python dependencies and external tools bundled together. No additional software installation is required.

## Requirements

- **Operating System**: Windows 10 or later (64-bit)
- **No additional software required** - all dependencies are bundled

## Installation

1. Download the latest `gamemanager-windows-*.zip` file from the [Releases](https://github.com/your-repo/releases) page
2. Extract the zip file to a location of your choice (e.g., `C:\Program Files\GameManager\`)
3. Run `gamemanager.exe`
4. Open your web browser and navigate to `http://localhost:5000`

## First Launch

1. **Access the Web Interface**
   - The application will start a local web server
   - Open your browser: `http://localhost:5000`
   - Default admin credentials:
     - Username: `admin`
     - **Password Setup**: On first login, you will be prompted to set up a password for the admin account

2. **Configure Your ROM Directory**
   - Go to **Configuration → Application Config**
   - Set the ROMs root directory path
   - Configure other settings as needed

3. **Configure Your Systems**
   - Go to **Configuration → System Configuration**
   - Add the game systems that you have in your roms directory

## External Tools

The following tools are bundled in the `tools/windows/` directory:

- **ffmpeg** (`tools/windows/` – same folder as yt-dlp.exe)
  - `ffmpeg.exe` - Video processing, cropping, encoding
  - `ffprobe.exe` - Video metadata extraction
  - Used for: Video downloads (yt-dlp merging), cropping, re-encoding, duration detection

- **ImageMagick** (`tools/windows/imagemagick/`)
  - `magick.exe` - ImageMagick 7 (replaces convert/identify/composite; same params)
  - Used for: Image resizing, format conversion, logo generation, 2D box art

- **yt-dlp** (`tools/windows/yt-dlp.exe`)
  - YouTube video downloader
  - Used for: Downloading game videos from YouTube

These tools are automatically detected and used by the application. You do not need to install them separately.

## Directory Structure

```
gamemanager_windows/
├── gamemanager.exe          # Main executable
├── _internal/               # PyInstaller runtime files (do not modify)
├── tools/                   # External tools
│   └── windows/            # Windows tool binaries
│       ├── ffmpeg.exe       # Video (same dir as yt-dlp so yt-dlp finds it)
│       ├── ffprobe.exe
│       ├── imagemagick/
│       └── yt-dlp.exe
├── var/                     # Application data
│   ├── config/              # Configuration files
│   ├── db/                  # Database files
│   └── task_logs/          # Task execution logs
└── README_WINDOWS.txt       # This file
```

## Configuration

Configuration files are stored in the `var/` directory:

- `var/config/config.json` - Main application configuration
- `var/config/scrappers.json` - Scraper settings
- `var/config/systems.json` - System configurations
- `var/db/` - Database files (LaunchBox, IGDB, etc.)
- `var/task_logs/` - Task execution logs

**Note**: Configuration files are created automatically on first run with default values.

## Troubleshooting

### Application Won't Start

1. **Check Windows Defender/Antivirus**
   - PyInstaller executables sometimes trigger false positives
   - Add an exception for `gamemanager.exe` and the installation directory
   - The executable is safe - it's built from the open-source code

2. **Check Console Window**
   - The application opens a console window showing startup messages
   - Check for error messages that might indicate the problem

3. **Verify File Extraction**
   - Ensure all files were extracted correctly
   - Do not run the executable from inside the zip file

4. **Check Port Availability**
   - The application uses port 5000 by default
   - If another application is using port 5000, change it in `var/config/config.json`

### External Tools Not Found

If you see errors about missing tools (ffmpeg, ImageMagick, yt-dlp):

1. Verify the `tools/windows/` directory exists
2. Check that the tool executables are present:
   - `tools/windows/ffmpeg.exe`
   - `tools/windows/ffprobe.exe`
   - `tools/windows/imagemagick/magick.exe`
   - `tools/windows/yt-dlp.exe`

3. If tools are missing, re-download the release package

### Media Files Not Displaying

1. Check file permissions on your ROMs directory
2. Verify media directory paths in configuration
3. Check browser console for errors (F12 → Console)
4. Ensure files exist in the correct locations

### Scraping Not Working

1. Verify scraper credentials in `var/config/scrappers.json`
2. Check rate limiting settings
3. Review task logs in `var/task_logs/`
4. Test API connectivity

## Building from Source

If you want to build the Windows executable yourself:

1. **Prerequisites**:
   - Windows 10/11 (64-bit)
   - Python 3.11 or higher
   - Git

2. **Setup**:
   ```bash
   git clone https://github.com/your-repo/gamemanager.git
   cd gamemanager
   pip install -r requirements.txt
   pip install pyinstaller
   ```

3. **Download External Tools**:
   - Download Windows versions of ffmpeg, ImageMagick, and yt-dlp
   - Place them in `tools/windows/` directory structure

4. **Build**:
   ```bash
   pyinstaller --clean gamemanager.spec
   ```

5. **Or use GitHub Actions**:
   - Push to the repository
   - GitHub Actions will automatically build the executable
   - Download the artifact from the Actions tab

## Performance Notes

- **First Launch**: May take 10-20 seconds to start (extracting PyInstaller files)
- **Memory Usage**: Typically 200-500 MB RAM
- **Disk Space**: ~200-300 MB for the application + tools
- **Network**: Requires internet connection for scraping features

## Security

- The executable is built from open-source code
- All dependencies are from trusted sources (PyPI, official tool releases)
- No telemetry or data collection
- All data stays on your local machine

## Support

For issues, questions, or contributions:

- **GitHub Issues**: [Report Issues](https://github.com/your-repo/issues)
- **Documentation**: See main [README.md](README.md)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)

## License

This software is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

Copyright (C) 2024 Alexandre Derumier <aderumier@gmail.com>
