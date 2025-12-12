#!/usr/bin/env python3
"""
PNG Extreme Aspect Ratio Filter
Scans PNG files in a source directory and moves images with extreme aspect ratios
(height > 6x width OR width > 6x height) to a target directory.
Landscape images (width > height) are rotated 90° clockwise before moving.

Usage:
    python png_extreme_aspect_filter.py <source_dir> <target_dir> [--preserve-structure] [--dry-run]

Example:
    python png_extreme_aspect_filter.py ./images ./filtered_images
    python png_extreme_aspect_filter.py ./images ./filtered_images --preserve-structure
    python png_extreme_aspect_filter.py ./images ./filtered_images --dry-run
"""

import os
import sys
import argparse
import shutil
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Error: Pillow is required. Install it with: pip install pillow")
    sys.exit(1)


def is_extreme_aspect_ratio(width, height, threshold=6.0):
    """
    Check if image has extreme aspect ratio.
    
    Args:
        width: Image width in pixels
        height: Image height in pixels
        threshold: Ratio threshold (default: 6.0)
    
    Returns:
        True if height > threshold * width OR width > threshold * height
    """
    if width == 0 or height == 0:
        return False
    
    # Check if height is more than threshold times width (very tall)
    if height > threshold * width:
        return True
    
    # Check if width is more than threshold times height (very wide)
    if width > threshold * height:
        return True
    
    return False


def get_image_dimensions(image_path):
    """
    Get image dimensions.
    
    Args:
        image_path: Path to image file
    
    Returns:
        Tuple of (width, height) or (None, None) if error
    """
    try:
        with Image.open(image_path) as img:
            return img.size  # Returns (width, height)
    except Exception as e:
        print(f"  ✗ Error reading image: {e}")
        return None, None


def move_image(source_path, target_path, width, height, preserve_structure=False, dry_run=False):
    """
    Move image file to target location, rotating if width > height.
    
    Args:
        source_path: Source file path
        target_path: Target file path
        width: Image width
        height: Image height
        preserve_structure: Create subdirectories if needed
        dry_run: If True, only print what would be done
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if preserve_structure:
            target_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            target_path.parent.mkdir(parents=True, exist_ok=True)
        
        if dry_run:
            rotate_info = " (would rotate 90° clockwise)" if width > height else ""
            print(f"  [DRY RUN] Would move: {source_path} -> {target_path}{rotate_info}")
            return True
        else:
            # If width > height, rotate 90 degrees clockwise before saving
            if width > height:
                try:
                    with Image.open(source_path) as img:
                        # Rotate 90 degrees clockwise (270 degrees counter-clockwise)
                        rotated_img = img.rotate(-90, expand=True)
                        rotated_img.save(str(target_path), 'PNG', optimize=True)
                    # Remove original file after successful save
                    os.remove(str(source_path))
                    return True
                except Exception as e:
                    print(f"  ✗ Error rotating/saving image: {e}")
                    return False
            else:
                # No rotation needed, just move
                shutil.move(str(source_path), str(target_path))
                return True
    except Exception as e:
        print(f"  ✗ Error moving file: {e}")
        return False


def filter_pngs_by_aspect_ratio(source_dir, target_dir, threshold=6.0, preserve_structure=False, dry_run=False):
    """
    Scan PNG files and move those with extreme aspect ratios to target directory.
    
    Args:
        source_dir: Source directory containing PNG files
        target_dir: Target directory for filtered images
        threshold: Aspect ratio threshold (default: 6.0)
        preserve_structure: Preserve directory structure in target
        dry_run: If True, only show what would be done without actually moving files
    """
    source_path = Path(source_dir).resolve()
    target_path = Path(target_dir).resolve()
    
    if not source_path.exists():
        print(f"Error: Source directory '{source_dir}' does not exist.")
        sys.exit(1)
    
    if not source_path.is_dir():
        print(f"Error: '{source_dir}' is not a directory.")
        sys.exit(1)
    
    # Create target directory
    target_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Source directory: {source_path}")
    print(f"Target directory: {target_path}")
    print(f"Aspect ratio threshold: {threshold}x")
    if preserve_structure:
        print(f"Mode: Preserving directory structure")
    else:
        print(f"Mode: Flat output")
    if dry_run:
        print(f"Mode: DRY RUN (no files will be moved)")
    print()
    
    # Find all PNG files recursively
    png_files = list(source_path.rglob("*.png")) + list(source_path.rglob("*.PNG"))
    
    if not png_files:
        print(f"No PNG files found in '{source_dir}' (including subdirectories)")
        return
    
    print(f"Found {len(png_files)} PNG file(s) to scan:")
    print("=" * 70)
    
    moved_count = 0
    scanned_count = 0
    error_count = 0
    
    for png_file in sorted(png_files):
        # Get relative path from source directory
        try:
            relative_to_source = png_file.relative_to(source_path)
        except ValueError:
            # If paths are on different drives (Windows), use absolute path
            relative_to_source = Path(png_file.name)
        
        display_path = str(relative_to_source) if relative_to_source != Path(png_file.name) else png_file.name
        print(f"\nScanning: {display_path}")
        
        scanned_count += 1
        
        # Get image dimensions
        width, height = get_image_dimensions(png_file)
        
        if width is None or height is None:
            error_count += 1
            continue
        
        # Check aspect ratio
        if is_extreme_aspect_ratio(width, height, threshold):
            # Determine target path
            if preserve_structure:
                target_file = target_path / relative_to_source
            else:
                target_file = target_path / png_file.name
                # Handle filename conflicts
                counter = 1
                while target_file.exists():
                    stem = png_file.stem
                    target_file = target_path / f"{stem}_{counter}{png_file.suffix}"
                    counter += 1
            
            aspect_ratio = max(width, height) / min(width, height)
            orientation = "tall" if height > width else "wide"
            
            print(f"  → Extreme aspect ratio detected: {width}x{height} ({aspect_ratio:.2f}:1, {orientation})")
            
            if move_image(png_file, target_file, width, height, preserve_structure, dry_run):
                moved_count += 1
                if not dry_run:
                    rotate_info = " (rotated)" if width > height else ""
                    print(f"  ✓ Moved to: {target_file.relative_to(target_path)}{rotate_info}")
        else:
            aspect_ratio = max(width, height) / min(width, height)
            print(f"  → Normal aspect ratio: {width}x{height} ({aspect_ratio:.2f}:1)")
    
    print()
    print("=" * 70)
    print(f"Summary:")
    print(f"  PNG files scanned: {scanned_count}")
    print(f"  Images moved: {moved_count}")
    print(f"  Errors: {error_count}")
    print(f"  Target directory: {target_path}")
    if dry_run:
        print(f"\n  Note: This was a DRY RUN. No files were actually moved.")


def main():
    parser = argparse.ArgumentParser(
        description='Scan PNG files and move images with extreme aspect ratios (height > 6x width OR width > 6x height) to target directory. Landscape images (width > height) are rotated 90° clockwise.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ./images ./filtered_images
  %(prog)s ./images ./filtered_images --preserve-structure
  %(prog)s ./images ./filtered_images --dry-run
  %(prog)s ./images ./filtered_images --threshold 8.0
        """
    )
    
    parser.add_argument(
        'source_dir',
        help='Source directory containing PNG files (will scan recursively)'
    )
    
    parser.add_argument(
        'target_dir',
        help='Target directory for images with extreme aspect ratios'
    )
    
    parser.add_argument(
        '--threshold',
        type=float,
        default=6.0,
        help='Aspect ratio threshold (default: 6.0, meaning height > 6x width OR width > 6x height)'
    )
    
    parser.add_argument(
        '--preserve-structure',
        action='store_true',
        help='Preserve directory structure in target directory'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without actually moving files'
    )
    
    args = parser.parse_args()
    
    filter_pngs_by_aspect_ratio(
        args.source_dir,
        args.target_dir,
        threshold=args.threshold,
        preserve_structure=args.preserve_structure,
        dry_run=args.dry_run
    )


if __name__ == '__main__':
    main()


