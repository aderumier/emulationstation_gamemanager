# PNG Aspect Ratio Filter

A standalone tool to scan PNG files in a source directory and move images with extreme aspect ratios (very tall or very wide) to a target directory. Landscape images (width > height) are automatically rotated 90° clockwise before moving.

## Features

- **Recursive Scanning**: Automatically scans all subdirectories for PNG files
- **Aspect Ratio Detection**: Identifies images where height > 3x width OR width > 3x height
- **Automatic Rotation**: Rotates landscape images (width > height) 90° clockwise before moving
- **Flexible Threshold**: Customizable aspect ratio threshold (default: 3.0)
- **Preserve Structure**: Option to maintain directory structure in target
- **Dry Run Mode**: Preview what would be moved without actually moving files
- **Progress Feedback**: Shows progress and image dimensions for each file

## Requirements

- Python 3.x
- Pillow (`PIL`)

## Installation

Install the required dependency:

```bash
pip install pillow
```

## Usage

### Basic Usage

Move images with extreme aspect ratios to a target directory:

```bash
python png_aspect_filter.py ./images ./filtered_images
```

### Preserve Directory Structure

Maintain the same directory structure in the target:

```bash
python png_aspect_filter.py ./images ./filtered_images --preserve-structure
```

### Dry Run (Preview)

See what would be moved without actually moving files:

```bash
python png_aspect_filter.py ./images ./filtered_images --dry-run
```

### Custom Threshold

Use a different aspect ratio threshold (e.g., 4.0 instead of 3.0):

```bash
python png_aspect_filter.py ./images ./filtered_images --threshold 4.0
```

### Examples

```bash
# Basic usage - move extreme aspect ratio images
python png_aspect_filter.py ./images ./filtered_images

# Preserve directory structure
python png_aspect_filter.py /path/to/images /path/to/filtered --preserve-structure

# Preview before moving
python png_aspect_filter.py ./images ./filtered_images --dry-run

# Use 4:1 threshold instead of 3:1
python png_aspect_filter.py ./images ./filtered_images --threshold 4.0
```

## How It Works

1. **Recursively scans** the source directory and all subdirectories for `.png` and `.PNG` files
2. For each PNG file found:
   - Reads image dimensions using Pillow
   - Calculates aspect ratio
   - Checks if height > threshold × width OR width > threshold × height
   - If extreme aspect ratio detected:
     - If width > height (landscape), rotates the image 90° clockwise
     - Moves the file to target directory
3. Provides progress feedback showing:
   - File being scanned
   - Image dimensions and aspect ratio
   - Whether rotation will be applied
   - Whether file was moved
4. Displays a summary at the end

## Aspect Ratio Detection

The tool identifies images with extreme aspect ratios:

- **Very Tall Images**: Height > threshold × width
  - Example: 100x400 pixels (4:1 ratio) with threshold 3.0
- **Very Wide Images**: Width > threshold × height
  - Example: 400x100 pixels (4:1 ratio) with threshold 3.0

Default threshold is 3.0, meaning:
- Images taller than 3:1 (e.g., 100x300, 200x600)
- Images wider than 3:1 (e.g., 300x100, 600x200)

## Output Modes

### Default Mode
- All filtered images moved to target root directory
- Filename conflicts handled with numeric suffixes

### Preserve Structure Mode (`--preserve-structure`)
- Maintains the same directory structure as the source
- Example: `images/subfolder/image.png` → `filtered_images/subfolder/image.png`

## Summary

The tool displays a summary showing:
- Number of PNG files scanned
- Number of images moved
- Number of errors encountered
- Target directory location

## Notes

- The tool **moves** files (not copies), removing them from the source directory
- Landscape images (width > height) are **rotated 90° clockwise** before being moved
- Portrait images (height > width) are moved without rotation
- Use `--dry-run` to preview changes before actually moving files
- Images that don't meet the threshold remain in the source directory
- If a file can't be read (corrupted, wrong format, etc.), it's skipped and counted as an error
- The target directory is created automatically if it doesn't exist

## Use Cases

This tool is useful for:
- Separating banner/panoramic images from regular images
- Filtering out very tall vertical images
- Organizing images by aspect ratio
- Cleaning up image collections

