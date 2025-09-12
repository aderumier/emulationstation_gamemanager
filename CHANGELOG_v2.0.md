# GameManager v2.0 Release Notes

## 🎉 Major Release - v2.0

### 🆕 New Features

#### SteamGridDB Integration
- **Complete SteamGridDB API Integration**: Full support for SteamGridDB API with authentication
- **SteamGridDB Scrap Preferences Modal**: User-friendly interface to configure SteamGridDB scraping options
- **Media Field Selection**: Choose which media types to download (Grids, Logos, Heroes)
- **Overwrite Media Fields Option**: Control whether to overwrite existing media files
- **Batch Processing**: Process 10 games in parallel for improved performance
- **Smart Game Name Search**: Search by game name when Steam ID is not available
- **Media Format Conversion**: Automatic conversion to target formats specified in config.json

#### Enhanced Game Management
- **Improved Duplicate Detection**: Extended to include all ID fields (igdbid, screenscraperid, steamid, steamgridid)
- **Better ID Field Handling**: Proper integer parsing and null handling for all ID fields
- **Enhanced ROM Scan**: Fixed gamelist.xml updates in var/gamelists directory
- **Parentheses Preservation**: Smart preservation of text in parentheses from original game names and ROM filenames

#### LaunchBox Integration Improvements
- **Fixed Force Download**: Corrected forceDownloadImages cookie propagation to image download tasks
- **Robust Metadata Lookup**: Improved LaunchBox ID lookup with type-agnostic matching
- **Better Error Handling**: Enhanced error handling and logging throughout the system

### 🔧 Technical Improvements

#### Code Quality
- **Async Processing**: Improved async/await patterns for better performance
- **Error Handling**: Enhanced error handling with proper logging
- **Code Organization**: Better separation of concerns and modular design
- **Type Safety**: Improved type hints and validation

#### Configuration Management
- **Dynamic Config Loading**: Real-time configuration loading for image conversion
- **Cookie Management**: Improved client-side cookie handling for user preferences
- **Field Mapping**: Enhanced field mapping between different data sources

#### Performance Optimizations
- **Parallel Processing**: Batch processing for API calls and media downloads
- **Caching**: Improved caching mechanisms for better performance
- **Memory Management**: Better memory usage patterns

### 🐛 Bug Fixes

#### SteamGridDB
- Fixed API authentication issues
- Corrected media download paths (added missing /media/ subdirectory)
- Fixed format conversion not working with config.json settings
- Resolved division by zero errors in progress calculation

#### LaunchBox
- Fixed game deletion bug when scraping games with same name but different ROM files
- Corrected forceDownloadImages cookie not being forwarded to image download tasks
- Fixed metadata cache lookup issues with type mismatches
- Resolved parentheses preservation logic

#### General
- Fixed multiple indentation errors throughout the codebase
- Corrected AG Grid sorting for integer ID fields
- Fixed null handling for empty ID fields
- Resolved ROM scan confirmation not updating gamelist.xml

### 📦 Package Updates

#### Debian Package
- Updated to version 2.0-1
- All dependencies updated and verified
- Improved package structure and metadata

#### Docker Image
- Updated to use Debian package 2.0-1
- Enhanced Dockerfile with better security practices
- Updated version labels and metadata

### 🚀 Installation

#### Debian Package
```bash
sudo dpkg -i gamemanager_2.0-1_all.deb
```

#### Docker
```bash
docker pull aderumier/gamemanager:2.0
# or
docker pull aderumier/gamemanager:latest
```

### 🔄 Migration from v1.9.5

This is a major version update with significant new features. The upgrade should be seamless, but please note:

1. **New SteamGridDB Features**: You'll need to configure your SteamGridDB API key in the new preferences modal
2. **Enhanced Duplicate Detection**: The duplicate detection now includes more ID fields
3. **Improved Media Handling**: Media files are now properly organized in /media/ subdirectories
4. **Better Configuration**: Some configuration options have been enhanced for better user experience

### 📋 System Requirements

- Python 3.8+
- Debian 13+ (or equivalent)
- Docker (optional)
- 2GB RAM minimum
- 10GB free disk space

### 🎯 What's Next

- Continued improvements to SteamGridDB integration
- Enhanced media management features
- Performance optimizations
- Additional data source integrations

---

**Release Date**: January 12, 2025  
**Version**: 2.0-1  
**Docker Image**: aderumier/gamemanager:2.0  
**Git Tag**: v2.0
