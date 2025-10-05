# Find Unused ROMs Script

This Python script helps you identify files and directories in your ROMs folder that are not referenced in a specific system's gamelist.xml file. This is useful for cleaning up your ROM collection and identifying orphaned files. The script can delete unused files in the root directory only, and will only identify unused directories (for safety).

## Features

- Scans a specific system's gamelist.xml file directly from `roms/<system>/gamelist.xml`
- Finds files and directories in the specific system's roms folder that are not referenced
- Excludes `media/` folders and `gamelist.xml` files from the search
- Provides summary statistics
- Handles broken pipe errors gracefully (useful with `head`, `tail`, etc.)

## Usage

### Basic Usage (Required: specify system)
```bash
python3 find_unused_roms.py --system nes
python3 find_unused_roms.py --system amstradcpc
python3 find_unused_roms.py --system lcdgames
```

### Show Only Files or Directories
```bash
python3 find_unused_roms.py --system nes --show-files
python3 find_unused_roms.py --system nes --show-dirs
```

### Limit Results
```bash
python3 find_unused_roms.py --system nes --limit 20
```

### Combine Options
```bash
python3 find_unused_roms.py --system nes --show-files --limit 10
```

### Delete Unused Files (DANGEROUS!)
```bash
python3 find_unused_roms.py --system nes --delete
python3 find_unused_roms.py --system lcdgames --delete --dry-run
```

## Examples

### Find all unused files and directories for NES
```bash
python3 find_unused_roms.py --system nes
```

### Find unused files for LCD Games system only
```bash
python3 find_unused_roms.py --system lcdgames --show-files
```

### Find first 20 unused directories for XBLA
```bash
python3 find_unused_roms.py --system xbla --show-dirs --limit 20
```

### Dry run - see what would be deleted without actually deleting
```bash
python3 find_unused_roms.py --system nes --delete --dry-run
```

### Actually delete unused files (with confirmation prompt)
```bash
python3 find_unused_roms.py --system nes --delete
```

## Output

The script provides:
- A summary of ROM paths found in the system's gamelist.xml file
- A list of unused files (not referenced in the gamelist.xml)
- A list of unused directories (containing no referenced files)
- Total counts for each category

## Safety Features

- **Dry Run Mode**: Use `--dry-run` with `--delete` to see what would be deleted without actually deleting
- **Confirmation Prompt**: When using `--delete`, the script asks for explicit confirmation before deleting
- **Detailed Preview**: Shows examples of files that will be deleted before asking for confirmation
- **Error Handling**: Continues deletion even if some files fail, and reports errors at the end
- **Files Only**: Only deletes files, never directories (safety feature to prevent accidental data loss)
- **Root Directory Only**: Only deletes files in the root directory of the system, not in subdirectories (additional safety layer)

## Notes

- The script requires a `--system` parameter to specify which system to check
- It looks for `gamelist.xml` directly in `roms/<system>/gamelist.xml`
- The script automatically excludes `media/` directories and `gamelist.xml` files from the search
- Paths are normalized to use forward slashes for consistency
- The script handles XML parsing errors gracefully
- Results are sorted alphabetically for easy reading
- **⚠️ WARNING**: The `--delete` option permanently removes files and directories. Use with caution!