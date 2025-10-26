# Import Medias Feature

## Overview
The Import Medias feature allows users to import media files from a source directory into their game collection's media folders. This is useful for bulk importing media files that have been collected separately.

## Features

### 1. **Submenu Integration**
- Added "Import Medias" submenu under "Current System" main menu
- Accessible via: Current System → Import Medias

### 2. **Modal Interface**
- **Source Directory Selection**: Choose from available subdirectories in `./roms/<system>/media/import/`
- **Target Media Field**: Select which gamelist media field to populate (from config.json)
- **Overwrite Option**: Checkbox to control whether existing media should be replaced
- **Matching Algorithm Info**: Clear explanation of the 4-level matching system

### 3. **4-Level Matching Algorithm**
The system uses a sophisticated matching algorithm with the following priority:

1. **Exact Filename Match**: Media filename (without extension) = ROM filename (without extension)
2. **Game Name Match**: Media filename (without extension) = Game name (case-insensitive)
3. **Normalized with Parentheses**: Both names normalized with parentheses preserved
4. **Normalized without Parentheses**: Both names normalized with parentheses removed

### 4. **File Operations**
- **Renaming**: Files are renamed to match ROM filename + original extension
- **Moving**: Files are moved from source directory to appropriate media directory
- **Gamelist Updates**: Target field is updated with the new media path
- **Overwrite Control**: Respects the overwrite setting for existing media

## API Endpoints

### GET `/api/import-medias/source-directories/<system_name>`
Returns available source directories for the specified system.

**Response:**
```json
{
  "directories": ["folder1", "folder2", "folder3"]
}
```

### POST `/api/import-medias`
Starts an import medias task.

**Request Body:**
```json
{
  "system_name": "mame",
  "source_directory": "sample-medias",
  "target_field": "boxart",
  "overwrite_existing": false
}
```

**Response:**
```json
{
  "success": true,
  "task_id": "uuid",
  "message": "Import medias task queued successfully"
}
```

## Task Queue Integration

The Import Medias feature is fully integrated with the existing task queue system:

- **Task Type**: `import_medias`
- **Background Processing**: Runs in separate thread
- **Progress Tracking**: Real-time progress updates
- **Cancellation Support**: Can be cancelled mid-process
- **Error Handling**: Comprehensive error reporting
- **Gamelist Updates**: Automatic gamelist saving and frontend refresh

## Directory Structure

```
roms/
└── <system_name>/
    └── media/
        └── import/
            ├── folder1/          # Source directory 1
            │   ├── game1.png
            │   ├── game2.jpg
            │   └── game3.png
            ├── folder2/          # Source directory 2
            │   └── ...
            └── folder3/          # Source directory 3
                └── ...
```

## Usage Example

1. **Prepare Media Files**: Place media files in `./roms/<system>/media/import/<folder>/`
2. **Open Import Modal**: Current System → Import Medias
3. **Select Source**: Choose the folder containing your media files
4. **Choose Target**: Select which media field to populate (boxart, screenshot, etc.)
5. **Set Overwrite**: Choose whether to replace existing media
6. **Start Import**: Click "Start Import" to begin the process
7. **Monitor Progress**: Watch the task progress in the task queue
8. **Review Results**: Check the task log for detailed results

## Technical Implementation

### Frontend (JavaScript)
- Modal management and form handling
- API communication for directory scanning and task initiation
- Real-time progress updates via WebSocket
- Error handling and user feedback

### Backend (Python)
- Directory scanning and validation
- 4-level matching algorithm implementation
- File operations (move, rename)
- Gamelist XML updates
- Task queue integration
- Cancellation support

### Matching Algorithm Details
```python
# Level 1: Exact filename match
if media_name_without_ext == rom_name_without_ext:
    matched_file = media_file

# Level 2: Game name match
if media_name_without_ext.lower() == game_name.lower():
    matched_file = media_file

# Level 3: Normalized with parentheses
if normalize_game_name(media_name_without_ext, remove_parentheses=False) == \
   normalize_game_name(rom_name_without_ext, remove_parentheses=False):
    matched_file = media_file

# Level 4: Normalized without parentheses
if normalize_game_name(media_name_without_ext, remove_parentheses=True) == \
   normalize_game_name(rom_name_without_ext, remove_parentheses=True):
    matched_file = media_file
```

## Benefits

1. **Bulk Import**: Import multiple media files at once
2. **Smart Matching**: Sophisticated algorithm handles various naming conventions
3. **Flexible Source**: Support for multiple source directories
4. **Safe Operation**: Overwrite control prevents accidental data loss
5. **Progress Tracking**: Real-time feedback on import progress
6. **Cancellation**: Can stop the process if needed
7. **Integration**: Seamlessly integrates with existing media management

## Future Enhancements

- **Preview Mode**: Show what files would be matched before importing
- **Batch Operations**: Import to multiple media fields simultaneously
- **File Validation**: Check file formats and dimensions
- **Duplicate Detection**: Handle duplicate media files intelligently
- **Backup Creation**: Create backups before overwriting existing media
