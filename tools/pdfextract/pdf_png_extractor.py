#!/usr/bin/env python3
"""
PDF PNG Extractor
Extracts all PNG images from all PDF files in a source directory (recursively).
Processes multiple PDFs in parallel using multiple CPU cores for faster extraction.

Based on: https://github.com/gsmatheus/pdf-image-extractor

Usage:
    python pdf_png_extractor.py <source_dir> [output_dir] [--preserve-structure] [--flat] [--workers N]

Example:
    python pdf_png_extractor.py ./pdfs ./extracted_images
    python pdf_png_extractor.py ./pdfs --preserve-structure
    python pdf_png_extractor.py ./pdfs ./output --flat
    python pdf_png_extractor.py ./pdfs --workers 4
"""

import os
import sys
import argparse
from pathlib import Path
from PIL import Image
import io
from multiprocessing import Pool, cpu_count
from functools import partial

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF is required. Install it with: pip install pymupdf")
    sys.exit(1)


def extract_png_from_pdf(pdf_path, output_dir, pdf_name, relative_path=""):
    """
    Extract PNG images from a single PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save extracted images
        pdf_name: Base name of the PDF (without extension)
        relative_path: Relative path prefix for preserving directory structure
    
    Returns:
        Number of images extracted
    """
    try:
        pdf_document = fitz.open(pdf_path)
        image_count = 0
        
        # Create subdirectory if preserving structure
        if relative_path:
            target_dir = Path(output_dir) / relative_path
            target_dir.mkdir(parents=True, exist_ok=True)
        else:
            target_dir = Path(output_dir)
        
        # Iterate over each page in the PDF
        for page_number in range(len(pdf_document)):
            page = pdf_document.load_page(page_number)
            images = page.get_images(full=True)
            
            # Extract each image
            for img_index, img in enumerate(images):
                try:
                    xref = img[0]
                    base_image = pdf_document.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"].lower()
                    
                    # Convert to PNG if not already PNG
                    image_filename = f"{pdf_name}_page{page_number + 1}.png"
                    image_path = target_dir / image_filename
                    
                    # Load image and convert to PNG
                    img_pil = Image.open(io.BytesIO(image_bytes))
                    
                    # Convert RGBA to RGB if needed (for JPEG compatibility)
                    if img_pil.mode == 'RGBA':
                        # Keep RGBA for PNG
                        img_pil.save(str(image_path), 'PNG', optimize=True)
                    else:
                        # Convert other modes to RGB then PNG
                        if img_pil.mode != 'RGB':
                            img_pil = img_pil.convert('RGB')
                        img_pil.save(str(image_path), 'PNG', optimize=True)
                    
                    image_count += 1
                    display_path = str(image_path.relative_to(output_dir)) if relative_path else image_filename
                    print(f"  ✓ Extracted: {display_path}")
                    
                except Exception as e:
                    print(f"  ✗ Error extracting image {img_index + 1} from page {page_number + 1}: {e}")
                    continue
        
        pdf_document.close()
        return image_count
        
    except Exception as e:
        print(f"  ✗ Error processing PDF: {e}")
        return 0


def check_if_already_extracted(pdf_name, output_dir, relative_path=""):
    """
    Check if images have already been extracted for a PDF.
    
    Args:
        pdf_name: Base name of the PDF (without extension)
        output_dir: Output directory
        relative_path: Relative path subdirectory
    
    Returns:
        True if images already exist, False otherwise
    """
    if relative_path:
        check_dir = Path(output_dir) / relative_path
    else:
        check_dir = Path(output_dir)
    
    if not check_dir.exists():
        return False
    
    # Check if any images with this PDF name prefix exist
    pattern = f"{pdf_name}_page*.png"
    existing_images = list(check_dir.glob(pattern))
    
    return len(existing_images) > 0


def process_single_pdf(args):
    """
    Process a single PDF file (for parallel processing).
    
    Args:
        args: Tuple of (pdf_file, source_path, output_dir, preserve_structure, flat_output)
    
    Returns:
        Tuple of (pdf_file, images_extracted, status, display_path, pdf_name, relative_path)
    """
    pdf_file, source_path, output_dir, preserve_structure, flat_output = args
    
    try:
        # Get relative path from source directory
        try:
            relative_to_source = pdf_file.relative_to(source_path)
        except ValueError:
            # If paths are on different drives (Windows), use absolute path
            relative_to_source = Path(pdf_file.name)
        
        # Determine output subdirectory and PDF name
        if flat_output:
            # Flat output: use just the filename (no directory prefix)
            pdf_name = pdf_file.stem
            relative_path = ""
        elif preserve_structure:
            # Preserve structure: use relative path as subdirectory
            relative_path = str(relative_to_source.parent) if relative_to_source.parent != Path('.') else ""
            pdf_name = pdf_file.stem
        else:
            # Default: all in root, use just the filename (no directory prefix)
            pdf_name = pdf_file.stem
            relative_path = ""
        
        # Display relative path for better visibility
        display_path = str(relative_to_source) if relative_to_source != Path(pdf_file.name) else pdf_file.name
        
        # Check if already extracted
        if check_if_already_extracted(pdf_name, str(output_dir), relative_path):
            return (pdf_file, 0, 'skipped', display_path, pdf_name, relative_path)
        
        # Extract images
        images_extracted = extract_png_from_pdf(str(pdf_file), str(output_dir), pdf_name, relative_path)
        
        if images_extracted > 0:
            return (pdf_file, images_extracted, 'success', display_path, pdf_name, relative_path)
        else:
            return (pdf_file, 0, 'no_images', display_path, pdf_name, relative_path)
            
    except Exception as e:
        return (pdf_file, 0, f'error: {str(e)}', str(pdf_file), '', '')


def extract_pngs_from_directory(source_dir, output_dir=None, preserve_structure=False, flat_output=False, max_workers=None):
    """
    Extract PNG images from all PDF files in a source directory (recursively).
    
    Args:
        source_dir: Directory containing PDF files
        output_dir: Directory to save extracted images (default: source_dir/extracted_pngs)
        preserve_structure: Preserve directory structure in output
        flat_output: Put all images in a single flat directory (overrides preserve_structure)
        max_workers: Number of parallel workers (default: number of CPU cores)
    """
    source_path = Path(source_dir).resolve()
    
    if not source_path.exists():
        print(f"Error: Source directory '{source_dir}' does not exist.")
        sys.exit(1)
    
    if not source_path.is_dir():
        print(f"Error: '{source_dir}' is not a directory.")
        sys.exit(1)
    
    # Set default output directory if not provided
    if output_dir is None:
        output_dir = source_path / "extracted_pngs"
    else:
        output_dir = Path(output_dir).resolve()
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine number of workers
    if max_workers is None:
        max_workers = cpu_count()
    elif max_workers <= 0:
        max_workers = cpu_count()
    
    print(f"Source directory: {source_path}")
    print(f"Output directory: {output_dir}")
    print(f"Parallel processing: {max_workers} worker(s)")
    if preserve_structure and not flat_output:
        print(f"Mode: Preserving directory structure")
    elif flat_output:
        print(f"Mode: Flat output (all images in one directory)")
    else:
        print(f"Mode: Default (all images in output root)")
    print()
    
    # Find all PDF files recursively
    pdf_files = list(source_path.rglob("*.pdf")) + list(source_path.rglob("*.PDF"))
    
    if not pdf_files:
        print(f"No PDF files found in '{source_dir}' (including subdirectories)")
        return
    
    print(f"Found {len(pdf_files)} PDF file(s) to process (including subdirectories):")
    print("=" * 70)
    
    # Prepare arguments for parallel processing
    process_args = [
        (pdf_file, source_path, output_dir, preserve_structure, flat_output)
        for pdf_file in sorted(pdf_files)
    ]
    
    total_images = 0
    processed_files = 0
    skipped_files = 0
    error_files = 0
    
    # Process PDFs in parallel
    if max_workers > 1 and len(pdf_files) > 1:
        print(f"\nProcessing {len(pdf_files)} PDFs in parallel using {max_workers} workers...\n")
        with Pool(processes=max_workers) as pool:
            results = pool.map(process_single_pdf, process_args)
        
        # Process results and display output
        for pdf_file, images_extracted, status, display_path, pdf_name, relative_path in results:
            if status == 'skipped':
                print(f"Skipping (already extracted): {display_path}")
                skipped_files += 1
            elif status == 'success':
                print(f"Processing: {display_path}")
                print(f"  → Extracted {images_extracted} image(s)")
                total_images += images_extracted
                processed_files += 1
            elif status == 'no_images':
                print(f"Processing: {display_path}")
                print(f"  → No images found")
            else:
                # Error
                print(f"Processing: {display_path}")
                print(f"  ✗ Error: {status}")
                error_files += 1
    else:
        # Sequential processing (for single file or single worker)
        for pdf_file, images_extracted, status, display_path, pdf_name, relative_path in [process_single_pdf(args) for args in process_args]:
            if status == 'skipped':
                print(f"\nSkipping (already extracted): {display_path}")
                skipped_files += 1
            elif status == 'success':
                print(f"\nProcessing: {display_path}")
                print(f"  → Extracted {images_extracted} image(s)")
                total_images += images_extracted
                processed_files += 1
            elif status == 'no_images':
                print(f"\nProcessing: {display_path}")
                print(f"  → No images found")
            else:
                # Error
                print(f"\nProcessing: {display_path}")
                print(f"  ✗ Error: {status}")
                error_files += 1
    
    print()
    print("=" * 70)
    print(f"Summary:")
    print(f"  PDF files processed: {processed_files}/{len(pdf_files)}")
    print(f"  PDF files skipped (already extracted): {skipped_files}")
    if error_files > 0:
        print(f"  PDF files with errors: {error_files}")
    print(f"  Total images extracted: {total_images}")
    print(f"  Output directory: {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description='Extract PNG images from all PDF files in a source directory (recursively scans subdirectories)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ./pdfs
  %(prog)s ./pdfs ./output_images
  %(prog)s ./pdfs --preserve-structure
  %(prog)s ./pdfs ./output --flat
  %(prog)s /path/to/pdfs /path/to/output --preserve-structure
        """
    )
    
    parser.add_argument(
        'source_dir',
        help='Source directory containing PDF files (will scan recursively)'
    )
    
    parser.add_argument(
        'output_dir',
        nargs='?',
        default=None,
        help='Output directory for extracted PNG images (default: <source_dir>/extracted_pngs)'
    )
    
    parser.add_argument(
        '--preserve-structure',
        action='store_true',
        help='Preserve directory structure in output (creates subdirectories matching source structure)'
    )
    
    parser.add_argument(
        '--flat',
        action='store_true',
        dest='flat_output',
        help='Put all images in a single flat directory'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=None,
        metavar='N',
        help='Number of parallel workers (default: number of CPU cores, use 1 for sequential processing)'
    )
    
    args = parser.parse_args()
    
    extract_pngs_from_directory(
        args.source_dir, 
        args.output_dir, 
        preserve_structure=args.preserve_structure,
        flat_output=args.flat_output,
        max_workers=args.workers
    )


if __name__ == '__main__':
    main()

