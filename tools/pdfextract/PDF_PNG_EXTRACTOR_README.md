# PDF PNG Extractor

A standalone tool to extract all PNG images from all PDF files in a source directory.

Based on the [pdf-image-extractor](https://github.com/gsmatheus/pdf-image-extractor) project.

## Features

- **Recursive Scanning**: Automatically scans all subdirectories for PDF files
- **Parallel Processing**: Processes multiple PDFs simultaneously using multiple CPU cores for faster extraction
- **Batch Processing**: Processes all PDF files in a directory tree automatically
- **Skip Already Extracted**: Automatically skips PDFs that have already been extracted (checks for existing images)
- **PNG Conversion**: Converts all extracted images to PNG format
- **Progress Feedback**: Shows progress for each PDF file processed
- **Error Handling**: Gracefully handles errors and continues processing
- **Flexible Output Options**:
  - Default: All images in output root directory (uses PDF filename only, no directory prefix)
  - `--preserve-structure`: Maintains directory structure in output
  - `--flat`: All images in one directory (uses PDF filename only)
- **Configurable Workers**: Control the number of parallel workers with `--workers` option

## Requirements

- Python 3.x
- PyMuPDF (`pymupdf`)
- Pillow (`PIL`)

## Installation

Install the required dependencies:

```bash
pip install -r pdf_png_extractor_requirements.txt
```

Or install manually:

```bash
pip install pymupdf pillow
```

## Usage

### Basic Usage

Extract PNG images from all PDFs in a directory and subdirectories (outputs to `source_dir/extracted_pngs`):

```bash
python pdf_png_extractor.py ./pdfs
```

### Custom Output Directory

Specify a custom output directory:

```bash
python pdf_png_extractor.py ./pdfs ./output_images
```

### Preserve Directory Structure

Maintain the same directory structure in the output:

```bash
python pdf_png_extractor.py ./pdfs ./output --preserve-structure
```

This will create subdirectories in the output matching the source structure.

### Flat Output

Put all images in a single directory (includes path info in filenames to avoid conflicts):

```bash
python pdf_png_extractor.py ./pdfs ./output --flat
```

### Examples

```bash
# Extract from current directory's pdfs folder (recursively, parallel processing)
python pdf_png_extractor.py ./pdfs

# Extract to a specific output directory with 4 workers
python pdf_png_extractor.py /path/to/pdfs /path/to/output --workers 4

# Preserve directory structure
python pdf_png_extractor.py ~/Documents/pdfs ~/Documents/extracted_images --preserve-structure

# Flat output (all images in one directory)
python pdf_png_extractor.py ./pdfs ./output --flat

# Sequential processing (single worker, useful for debugging)
python pdf_png_extractor.py ./pdfs ./output --workers 1
```

## Output

### Default Mode
- Images are saved with the format: `{pdf_name}_page{page_number}.png`
- Uses only the PDF filename (no directory prefix)
- Example: `manual_page1.png`, `manual_page2.png`, `guide_page1.png`, etc.
- **Note**: If multiple PDFs with the same name exist in different subdirectories, images will overwrite each other. Use `--preserve-structure` to avoid conflicts.
- **Note**: If a page has multiple images, only the last one will be saved (images will overwrite). Assumes one image per page.

### Preserve Structure Mode (`--preserve-structure`)
- Maintains the same directory structure as the source
- Example: `pdfs/manuals/manual.pdf` → `output/manuals/manual_page1.png`
- **Note**: If a page has multiple images, only the last one will be saved (images will overwrite). Assumes one image per page.

### Flat Mode (`--flat`)
- All images in one directory
- Uses only the PDF filename (no directory prefix)
- Example: `manual_page1.png`, `manual_page2.png`
- **Note**: If multiple PDFs with the same name exist in different subdirectories, images will overwrite each other. Use `--preserve-structure` to avoid conflicts.
- **Note**: If a page has multiple images, only the last one will be saved (images will overwrite). Assumes one image per page.

### Summary
A summary is displayed at the end showing:
- Number of PDF files processed (including subdirectories)
- Number of PDF files skipped (already extracted)
- Total images extracted
- Output directory location
- Processing mode used

## How It Works

1. **Recursively scans** the source directory and all subdirectories for `.pdf` and `.PDF` files
2. **Parallel Processing**: 
   - By default, uses all available CPU cores to process multiple PDFs simultaneously
   - Can be configured with `--workers N` option
   - Significantly faster when processing many PDF files
3. For each PDF file found:
   - Checks if images have already been extracted (looks for existing PNG files with matching prefix)
   - If already extracted, skips the PDF and continues to the next one
   - If not extracted:
     - Opens the PDF using PyMuPDF
     - Iterates through each page
     - Extracts all images from each page
     - Converts images to PNG format
     - Saves them according to the selected output mode
4. Provides progress feedback showing which file is being processed or skipped
5. Displays a summary at the end including skipped files count

## Notes

- The tool preserves image quality and converts all images to PNG format
- RGBA images (with transparency) are preserved as PNG
- Other image formats are converted to RGB then saved as PNG
- If an image extraction fails, the tool continues with the next image
- The output directory is created automatically if it doesn't exist
- **Already extracted PDFs are automatically skipped** - the tool checks for existing PNG files with the same PDF name prefix before processing
- To re-extract a PDF, delete its extracted images from the output directory first
- **Parallel processing** significantly speeds up extraction when processing many PDFs
  - Default: Uses all available CPU cores
  - Use `--workers 1` for sequential processing (useful for debugging or low-memory systems)
  - Use `--workers N` to specify a custom number of workers

