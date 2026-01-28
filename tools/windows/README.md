# Windows Tools Directory

This directory contains Windows executables for external tools required by GameManager.

## Directory Structure

```
tools/windows/
├── ffmpeg/
│   ├── ffmpeg.exe      # Video processing
│   └── ffprobe.exe     # Video metadata
├── imagemagick/
│   ├── convert.exe     # Image conversion
│   └── identify.exe    # Image information
└── yt-dlp.exe         # YouTube downloader
```

## Download Instructions

### FFmpeg

1. Visit: https://www.gyan.dev/ffmpeg/builds/
2. Download: `ffmpeg-release-essentials.zip`
3. Extract the zip file
4. Copy `ffmpeg.exe` and `ffprobe.exe` from `ffmpeg-*/bin/` to `tools/windows/ffmpeg/`

### ImageMagick

1. Visit: https://imagemagick.org/script/download.php
2. Download: Windows portable version (zip) or installer
3. If zip: Extract and copy `convert.exe` and `identify.exe` from `ImageMagick-*/bin/` to `tools/windows/imagemagick/`
4. If installer: Install and copy from installation directory (usually `C:\Program Files\ImageMagick-*/`)

### yt-dlp

1. Visit: https://github.com/yt-dlp/yt-dlp/releases/latest
2. Download: `yt-dlp.exe`
3. Place directly in `tools/windows/yt-dlp.exe`

## Note for GitHub Actions

The GitHub Actions workflow automatically downloads these tools during the build process. You only need to manually download them if building locally.
