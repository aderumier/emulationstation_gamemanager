# GameManager v1.8.3 Release Notes

## 🎯 Major Fixes & Improvements

### 🔧 LaunchBox Media Download Fix
- **Fixed critical bug** where LaunchBox media download was failing with 404 errors
- Now correctly reads game data from `var/gamelists/<system>/gamelist.xml` (where scraped games with LaunchBox IDs are stored)
- Properly writes media files to `roms/<system>/media/` directories
- Added comprehensive error handling with clear messages for different failure scenarios

### 📁 Enhanced ROM Scanning
- **Recursive directory scanning**: ROM scan now includes all subdirectories in `roms/<system>/`
- **Smart media exclusion**: Automatically excludes `media` folders from ROM scanning
- **Clean game names**: Games in subdirectories now get proper names using `basename()` instead of full paths
- **Path normalization**: Improved handling of relative paths for better compatibility

### 🛠️ Technical Improvements
- Fixed `apply_partial_match` function to use proper gamelist path resolution
- Enhanced error messages to distinguish between missing gamelists vs missing LaunchBox IDs
- Improved path comparison logic for better ROM file detection
- Better handling of games with missing ROM files during scanning

## 🐛 Bug Fixes

- **Fixed 404 errors** when downloading LaunchBox media for games
- **Fixed game name generation** for ROMs in subdirectories (now shows clean names like "game" instead of "subfolder/game")
- **Fixed system_path reference error** in media download functionality
- **Fixed hardcoded roms path** in partial match application

## 📋 What's New

### Enhanced Directory Structure Support
```
roms/nes/
├── game1.nes                    ← Scanned
├── subfolder1/
│   ├── game2.nes               ← Now scanned!
│   └── game3.zip               ← Now scanned!
├── subfolder2/
│   └── game4.nes               ← Now scanned!
└── media/                      ← Excluded from scanning
    ├── boxart/
    └── screenshots/
```

### Improved Error Messages
- Clear distinction between "Gamelist not found" vs "Game not found in gamelist"
- Better guidance when no LaunchBox IDs are present in a system
- More descriptive error messages for troubleshooting

## 🚀 Installation

### Debian Package
```bash
sudo dpkg -i gamemanager_1.8.3-1_all.deb
```

### Docker
```bash
docker run -d -p 5000:5000 \
  -v /path/to/roms:/opt/gamemanager/roms \
  -v /path/to/var:/opt/gamemanager/var \
  -e IGDB_CLIENT_ID=your_client_id \
  -e IGDB_CLIENT_SECRET=your_client_secret \
  aderumier/emulationstation_gamemanager:1.8.3
```

## 🔄 Migration Notes

- **No breaking changes** - fully backward compatible
- Existing gamelists will continue to work without modification
- New ROM scanning will automatically detect games in subdirectories
- LaunchBox media download will now work correctly for all systems

## 📊 Technical Details

- **Version**: 1.8.3-1
- **Docker Image**: `aderumier/emulationstation_gamemanager:1.8.3`
- **Docker Hub**: [aderumier/emulationstation_gamemanager](https://hub.docker.com/r/aderumier/emulationstation_gamemanager)
- **GitHub**: [aderumier/emulationstation_gamemanager](https://github.com/aderumier/emulationstation_gamemanager)

## 🎉 What's Working Better Now

1. **LaunchBox Media Download**: No more 404 errors when downloading media
2. **ROM Organization**: Support for organized ROM collections in subdirectories
3. **Game Names**: Clean, readable game names regardless of directory structure
4. **Error Handling**: Better feedback when things go wrong
5. **Path Management**: Consistent handling of file paths across the application

---

**Full Changelog**: https://github.com/aderumier/emulationstation_gamemanager/compare/v1.8.2...v1.8.3
