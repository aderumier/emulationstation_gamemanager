#!/bin/bash

# VHD Extractor Script
# Extracts a .vhd (FAT/FAT32) disk image from a source zip and creates an output zip
# with the extracted files (preserving directory structure) plus other files from source.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
CLEANUP_ON_EXIT=true
USE_QEMU_NBD=false
MODE=""
LOOP_DEVICE=""
NBD_DEVICE=""

# Cleanup function (for emergency cleanup only - each zip processes its own cleanup)
cleanup() {
    if [ "$CLEANUP_ON_EXIT" = true ]; then
        echo -e "${YELLOW}Emergency cleanup...${NC}"
        
        # Try to clean up any remaining mounts/devices
        # Note: In normal operation, each zip file handles its own cleanup
        for mnt in /tmp/tmp.*; do
            if [ -d "$mnt" ] && mountpoint -q "$mnt" 2>/dev/null; then
                echo "Unmounting $mnt..."
                sudo umount "$mnt" 2>/dev/null || true
                rmdir "$mnt" 2>/dev/null || true
            fi
        done
        
        # Clean up any temp directories that might be left
        for tmpdir in /tmp/tmp.*; do
            if [ -d "$tmpdir" ] && [[ "$tmpdir" =~ ^/tmp/tmp\.[A-Za-z0-9]+$ ]]; then
                # Only remove if it looks like our temp dirs and is empty or old
                if [ -z "$(ls -A "$tmpdir" 2>/dev/null)" ] || [ "$(find "$tmpdir" -maxdepth 0 -mmin +10)" ]; then
                    rm -rf "$tmpdir" 2>/dev/null || true
                fi
            fi
        done
    fi
}

# Setup trap for cleanup on exit
trap cleanup EXIT

# Usage function
usage() {
    cat << EOF
Usage: $0 <input_directory> <output_directory>

Processes all zip files in the input directory and creates corresponding output zips
in the output directory. For each source zip, extracts .vhd (FAT/FAT32) disk image
and creates an output zip containing:
  - All files from the .vhd (preserving directory structure)
  - All other files from the source zip (excluding the .vhd file) at root level
  - AUTOBOOT.DBP from the source zip's directory (if present) at root level

Arguments:
  input_directory    Directory containing source zip files
  output_directory  Directory where output zip files will be created

Requirements:
  - sudo access (for mounting loop devices)
  - unzip, zip, mount, losetup, umount commands
  - qemu-nbd recommended for VHD files (install: sudo apt-get install qemu-utils)

Example:
  $0 ./source_zips ./output_zips
EOF
    exit 1
}

# Check for required tools
check_requirements() {
    local missing_tools=()
    
    for tool in unzip zip mount losetup umount sudo; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        echo -e "${RED}Error: Missing required tools: ${missing_tools[*]}${NC}" >&2
        exit 1
    fi
    
    # Check if user can use sudo
    if ! sudo -n true 2>/dev/null; then
        echo -e "${YELLOW}Note: This script requires sudo privileges for mounting.${NC}"
        echo "You may be prompted for your password."
    fi
    
    # Check for qemu-nbd (preferred for VHD files)
    if command -v qemu-nbd &> /dev/null; then
        echo -e "${GREEN}Found qemu-nbd - will use it for VHD mounting (recommended)${NC}"
        export USE_QEMU_NBD=true
    else
        echo -e "${YELLOW}qemu-nbd not found - will try loop device mounting${NC}"
        echo -e "${YELLOW}For better VHD support, install qemu-utils: sudo apt-get install qemu-utils${NC}"
        export USE_QEMU_NBD=false
    fi
    
    # Check for blkid (needed for partition detection)
    if ! command -v blkid &> /dev/null; then
        echo -e "${YELLOW}Warning: blkid not found - partition detection may be limited${NC}"
    fi
}

# Parse arguments
if [ $# -ne 2 ]; then
    usage
fi

INPUT_DIR="$1"
OUTPUT_DIR="$2"

# Validate input directory exists
if [ ! -d "$INPUT_DIR" ]; then
    echo -e "${RED}Error: Input directory not found: $INPUT_DIR${NC}" >&2
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Convert to absolute paths
ORIGINAL_PWD=$(pwd)
INPUT_DIR_ABS=$(cd "$INPUT_DIR" && pwd)
OUTPUT_DIR_ABS=$(cd "$OUTPUT_DIR" && pwd)

echo -e "${GREEN}Input directory: $INPUT_DIR_ABS${NC}"
echo -e "${GREEN}Output directory: $OUTPUT_DIR_ABS${NC}"

# Find all zip files in input directory
ZIP_FILES=$(find "$INPUT_DIR_ABS" -maxdepth 1 -type f -iname "*.zip" | sort)

if [ -z "$ZIP_FILES" ]; then
    echo -e "${YELLOW}No zip files found in input directory: $INPUT_DIR_ABS${NC}"
    exit 0
fi

ZIP_COUNT=$(echo "$ZIP_FILES" | wc -l)
echo -e "${GREEN}Found $ZIP_COUNT zip file(s) to process${NC}"
echo ""

# Check requirements
check_requirements

# Function to process a single zip file
process_zip_file() {
    local SOURCE_ZIP="$1"
    local OUTPUT_ZIP="$2"
    local OUTPUT_CREATED=false
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Processing: $(basename "$SOURCE_ZIP")${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    # Cleanup function for this zip processing
    local_cleanup() {
        # Remove output zip if it was created but processing failed
        if [ "$OUTPUT_CREATED" = true ] && [ -f "$OUTPUT_ZIP" ]; then
            echo -e "${YELLOW}Removing incomplete output zip: $OUTPUT_ZIP${NC}"
            rm -f "$OUTPUT_ZIP"
        fi
    }
    
    # Create temporary directory for this zip
    local TEMP_DIR=$(mktemp -d)
    
    # Extract source zip
    echo -e "${GREEN}Extracting source zip: $SOURCE_ZIP${NC}"
    unzip -q "$SOURCE_ZIP" -d "$TEMP_DIR"

    # Find .vhd file
    local VHD_FILE=$(find "$TEMP_DIR" -type f -iname "*.vhd" | head -n 1)
    
    if [ -z "$VHD_FILE" ]; then
        echo -e "${RED}Error: No .vhd file found in source zip: $SOURCE_ZIP${NC}" >&2
        rm -rf "$TEMP_DIR"
        local_cleanup
        return 1
    fi
    
    echo -e "${GREEN}Found .vhd file: $VHD_FILE${NC}"
    
    # Create mount point
    local MOUNT_POINT=$(mktemp -d)
    local LOOP_DEVICE=""
    local NBD_DEVICE=""
    local MODE=""

    # Mount .vhd file - use qemu-nbd for VHD files (like test.sh), fallback to loop device
    echo "Mounting .vhd file..."
    
    # Determine file extension to decide mounting method
    local VHD_EXT="${VHD_FILE##*.}"
    VHD_EXT="${VHD_EXT,,}"
    
    local DEV_BASE=""
    if [ "$VHD_EXT" = "img" ] || [ "$USE_QEMU_NBD" = false ]; then
        # Use loop device for .img files or if qemu-nbd not available
        MODE="loop"
        echo "Using loop device mounting..."
        LOOP_DEVICE=$(sudo losetup --find --show --partscan "$VHD_FILE")
        DEV_BASE="$LOOP_DEVICE"
        echo -e "${GREEN}Loop device: $LOOP_DEVICE${NC}"
    else
        # Use qemu-nbd for VHD and other formats
        MODE="nbd"
        echo "Using qemu-nbd for VHD mounting..."
        
        # Ensure nbd module is loaded
        sudo modprobe nbd max_part=16 2>/dev/null || true
        
        # Find a free /dev/nbdX device - check more thoroughly and try to use different devices
        NBD_DEVICE=""
        # Try to find a device that's truly free (not just disconnected, but with no partitions)
        for d in /dev/nbd{0..15}; do
            # Check if device exists
            [ ! -b "$d" ] && continue
            
            # Disconnect first to ensure it's clean
            sudo qemu-nbd --disconnect "$d" 2>/dev/null || true
            sleep 0.1
            
            # Check if device is mounted
            if lsblk -no MOUNTPOINT "$d" 2>/dev/null | grep -q .; then
                continue
            fi
            # Check if device is in use by another process
            if sudo lsof "$d" >/dev/null 2>&1; then
                continue
            fi
            # Check if device has partitions mounted
            PARTITIONS_MOUNTED=false
            for p in "${d}"p*; do
                if [ -b "$p" ] && lsblk -no MOUNTPOINT "$p" 2>/dev/null | grep -q .; then
                    PARTITIONS_MOUNTED=true
                    break
                fi
            done
            if [ "$PARTITIONS_MOUNTED" = true ]; then
                continue
            fi
            # Device appears free
            NBD_DEVICE="$d"
            break
        done
        
        if [ -z "$NBD_DEVICE" ]; then
            echo -e "${RED}Error: No free /dev/nbd device found (tried /dev/nbd0..15)${NC}" >&2
            rm -rf "$TEMP_DIR" "$MOUNT_POINT"
            local_cleanup
            return 1
        fi
        
        # Connect to the VHD file (device was already disconnected in the loop above)
        if ! sudo qemu-nbd --connect="$NBD_DEVICE" "$VHD_FILE"; then
            echo -e "${RED}Error: Failed to connect qemu-nbd to $VHD_FILE${NC}" >&2
            rm -rf "$TEMP_DIR" "$MOUNT_POINT"
            local_cleanup
            return 1
        fi
        
        # Give kernel time and force partition re-read
        sleep 0.5
        sudo partprobe "$NBD_DEVICE" 2>/dev/null || true
        udevadm settle 2>/dev/null || true
        sleep 0.5
        
        DEV_BASE="$NBD_DEVICE"
        echo -e "${GREEN}Attached via nbd: $NBD_DEVICE${NC}"
    fi
    
    # Find FAT partition or filesystem
    local FAT_DEV=""
    
    # First try partitions (e.g., /dev/loop0p1 or /dev/nbd0p1)
    for p in "${DEV_BASE}"p*; do
        if [ -b "$p" ]; then
            local FS_TYPE=$(sudo blkid -o value -s TYPE "$p" 2>/dev/null || echo "")
            if [ "${FS_TYPE,,}" = "vfat" ]; then
                FAT_DEV="$p"
                break
            fi
        fi
    done
    
    # If no vfat partition found, try the whole device
    if [ -z "$FAT_DEV" ]; then
        local FS_TYPE=$(sudo blkid -o value -s TYPE "$DEV_BASE" 2>/dev/null || echo "")
        if [ "${FS_TYPE,,}" = "vfat" ]; then
            FAT_DEV="$DEV_BASE"
        fi
    fi
    
    if [ -z "$FAT_DEV" ]; then
        echo -e "${RED}Error: Could not find a FAT(vfat) filesystem in: $VHD_FILE${NC}" >&2
        echo -e "${YELLOW}Tip: Run 'sudo blkid ${DEV_BASE}*' to inspect partitions/filesystems${NC}" >&2
        # Cleanup
        if [ "$MODE" = "loop" ] && [ -n "$LOOP_DEVICE" ]; then
            sudo losetup -d "$LOOP_DEVICE" 2>/dev/null || true
        elif [ "$MODE" = "nbd" ] && [ -n "$NBD_DEVICE" ]; then
            sudo qemu-nbd --disconnect "$NBD_DEVICE" 2>/dev/null || true
        fi
        rm -rf "$TEMP_DIR" "$MOUNT_POINT"
        local_cleanup
        return 1
    fi
    
    echo -e "${GREEN}Found FAT filesystem: $FAT_DEV${NC}"
    
    # Ensure mount point exists and is a directory
    if [ ! -d "$MOUNT_POINT" ]; then
        echo -e "${RED}Error: Mount point does not exist: $MOUNT_POINT${NC}" >&2
        # Cleanup
        if [ "$MODE" = "loop" ] && [ -n "$LOOP_DEVICE" ]; then
            sudo losetup -d "$LOOP_DEVICE" 2>/dev/null || true
        elif [ "$MODE" = "nbd" ] && [ -n "$NBD_DEVICE" ]; then
            sudo qemu-nbd --disconnect "$NBD_DEVICE" 2>/dev/null || true
        fi
        rm -rf "$TEMP_DIR" "$MOUNT_POINT"
        local_cleanup
        return 1
    fi
    
    # Verify device is ready (for NBD, wait a bit more)
    if [ "$MODE" = "nbd" ]; then
        # Check if device is accessible
        if [ ! -b "$FAT_DEV" ]; then
            echo -e "${YELLOW}Waiting for device $FAT_DEV to be ready...${NC}"
            sleep 0.5
            if [ ! -b "$FAT_DEV" ]; then
                echo -e "${RED}Error: Device $FAT_DEV is not accessible${NC}" >&2
                sudo qemu-nbd --disconnect "$NBD_DEVICE" 2>/dev/null || true
                rm -rf "$TEMP_DIR" "$MOUNT_POINT"
                local_cleanup
                return 1
            fi
        fi
    fi
    
    echo "Mounting (read-only): $FAT_DEV"
    if ! sudo mount -o ro "$FAT_DEV" "$MOUNT_POINT"; then
        echo -e "${RED}Error: Failed to mount $FAT_DEV${NC}" >&2
        # Cleanup
        if [ "$MODE" = "loop" ] && [ -n "$LOOP_DEVICE" ]; then
            sudo losetup -d "$LOOP_DEVICE" 2>/dev/null || true
        elif [ "$MODE" = "nbd" ] && [ -n "$NBD_DEVICE" ]; then
            sudo qemu-nbd --disconnect "$NBD_DEVICE" 2>/dev/null || true
        fi
        rm -rf "$TEMP_DIR" "$MOUNT_POINT"
        local_cleanup
        return 1
    fi
    
    # Verify mount succeeded
    if ! mountpoint -q "$MOUNT_POINT" 2>/dev/null; then
        echo -e "${RED}Error: Mount verification failed for $MOUNT_POINT${NC}" >&2
        sudo umount "$MOUNT_POINT" 2>/dev/null || true
        if [ "$MODE" = "loop" ] && [ -n "$LOOP_DEVICE" ]; then
            sudo losetup -d "$LOOP_DEVICE" 2>/dev/null || true
        elif [ "$MODE" = "nbd" ] && [ -n "$NBD_DEVICE" ]; then
            sudo qemu-nbd --disconnect "$NBD_DEVICE" 2>/dev/null || true
        fi
        rm -rf "$TEMP_DIR" "$MOUNT_POINT"
        local_cleanup
        return 1
    fi
    
    # Create directory for extracted .vhd files
    local VHD_EXTRACT_DIR="$TEMP_DIR/vhd_extracted"
    mkdir -p "$VHD_EXTRACT_DIR"

    # Extract files from mounted .vhd, preserving directory structure
    echo -e "${GREEN}Extracting files from .vhd (preserving directory structure)...${NC}"
    
    # Verify mount point and extract directory exist and are accessible
    if [ ! -d "$MOUNT_POINT" ]; then
        echo -e "${RED}Error: Mount point does not exist: $MOUNT_POINT${NC}" >&2
        sudo umount "$MOUNT_POINT" 2>/dev/null || true
        if [ "$MODE" = "loop" ] && [ -n "$LOOP_DEVICE" ]; then
            sudo losetup -d "$LOOP_DEVICE" 2>/dev/null || true
        elif [ "$MODE" = "nbd" ] && [ -n "$NBD_DEVICE" ]; then
            sudo qemu-nbd --disconnect "$NBD_DEVICE" 2>/dev/null || true
        fi
        rm -rf "$TEMP_DIR" "$MOUNT_POINT"
        local_cleanup
        return 1
    fi
    
    if [ ! -d "$VHD_EXTRACT_DIR" ]; then
        echo -e "${RED}Error: Extract directory does not exist: $VHD_EXTRACT_DIR${NC}" >&2
        sudo umount "$MOUNT_POINT" 2>/dev/null || true
        if [ "$MODE" = "loop" ] && [ -n "$LOOP_DEVICE" ]; then
            sudo losetup -d "$LOOP_DEVICE" 2>/dev/null || true
        elif [ "$MODE" = "nbd" ] && [ -n "$NBD_DEVICE" ]; then
            sudo qemu-nbd --disconnect "$NBD_DEVICE" 2>/dev/null || true
        fi
        rm -rf "$TEMP_DIR" "$MOUNT_POINT"
        local_cleanup
        return 1
    fi
    
    # Use rsync if available for better directory structure preservation, otherwise use find+cp
    EXTRACT_SUCCESS=false
    if command -v rsync &> /dev/null; then
        # Use absolute paths and ensure we're in a safe directory
        MOUNT_POINT_ABS=$(cd "$MOUNT_POINT" && pwd)
        VHD_EXTRACT_DIR_ABS=$(cd "$VHD_EXTRACT_DIR" && pwd)
        
        # Run rsync from a safe directory (temp dir root) using absolute paths
        cd "$TEMP_DIR"
        set +e  # Temporarily disable exit on error to check rsync exit code
        rsync -a "${MOUNT_POINT_ABS}/" "${VHD_EXTRACT_DIR_ABS}/" 2>&1
        RSYNC_EXIT=$?
        set -e  # Re-enable exit on error
        if [ $RSYNC_EXIT -eq 0 ]; then
            EXTRACT_SUCCESS=true
        else
            echo -e "${RED}Error: rsync failed with exit code $RSYNC_EXIT${NC}" >&2
        fi
    else
        # Use find to copy all files and directories, preserving structure
        EXTRACT_COUNT=0
        while IFS= read -r -d '' item; do
            rel_path="${item#$MOUNT_POINT/}"
            target_path="$VHD_EXTRACT_DIR/$rel_path"
            if [ -d "$item" ]; then
                mkdir -p "$target_path"
            else
                mkdir -p "$(dirname "$target_path")"
                if cp "$item" "$target_path" 2>/dev/null; then
                    EXTRACT_COUNT=$((EXTRACT_COUNT + 1))
                fi
            fi
        done < <(find "$MOUNT_POINT" -mindepth 1 -print0 2>/dev/null)
        if [ $EXTRACT_COUNT -gt 0 ] || [ "$(ls -A "$VHD_EXTRACT_DIR" 2>/dev/null)" ]; then
            EXTRACT_SUCCESS=true
        else
            echo -e "${RED}Error: Failed to extract files from .vhd${NC}" >&2
        fi
    fi
    
    # Verify extraction succeeded and files were actually extracted BEFORE unmounting
    if [ "$EXTRACT_SUCCESS" = false ]; then
        echo -e "${RED}Error: Extraction command failed${NC}" >&2
        # Cleanup
        sudo umount "$MOUNT_POINT" 2>/dev/null || true
        if [ "$MODE" = "loop" ] && [ -n "$LOOP_DEVICE" ]; then
            sudo losetup -d "$LOOP_DEVICE" 2>/dev/null || true
        elif [ "$MODE" = "nbd" ] && [ -n "$NBD_DEVICE" ]; then
            sudo qemu-nbd --disconnect "$NBD_DEVICE" 2>/dev/null || true
        fi
        rm -rf "$TEMP_DIR" "$MOUNT_POINT"
        local_cleanup
        return 1
    fi
    
    # Verify files were actually extracted
    if [ ! "$(ls -A "$VHD_EXTRACT_DIR" 2>/dev/null)" ]; then
        echo -e "${RED}Error: No files found in extraction directory${NC}" >&2
        # Cleanup
        sudo umount "$MOUNT_POINT" 2>/dev/null || true
        if [ "$MODE" = "loop" ] && [ -n "$LOOP_DEVICE" ]; then
            sudo losetup -d "$LOOP_DEVICE" 2>/dev/null || true
        elif [ "$MODE" = "nbd" ] && [ -n "$NBD_DEVICE" ]; then
            sudo qemu-nbd --disconnect "$NBD_DEVICE" 2>/dev/null || true
        fi
        rm -rf "$TEMP_DIR" "$MOUNT_POINT"
        local_cleanup
        return 1
    fi
    
    # Unmount .vhd after successful extraction
    echo "Unmounting .vhd..."
    sudo umount "$MOUNT_POINT"
    
    # Detach device
    if [ "$MODE" = "loop" ] && [ -n "$LOOP_DEVICE" ]; then
        sudo losetup -d "$LOOP_DEVICE" 2>/dev/null || true
    elif [ "$MODE" = "nbd" ] && [ -n "$NBD_DEVICE" ]; then
        # Unmount any remaining partitions first
        for p in "${NBD_DEVICE}"p*; do
            if [ -b "$p" ]; then
                MOUNTED_WHERE=$(lsblk -no MOUNTPOINT "$p" 2>/dev/null | grep -v '^$' | head -n1)
                if [ -n "$MOUNTED_WHERE" ]; then
                    sudo umount "$p" 2>/dev/null || true
                fi
            fi
        done
        sleep 0.2
        sudo qemu-nbd --disconnect "$NBD_DEVICE" 2>/dev/null || true
        # Wait longer for NBD device to be fully released before next use
        sleep 1.0
    fi
    
    # Create directory for merged output (vhd files + other files at root level)
    local OUTPUT_TEMP_DIR="$TEMP_DIR/output"
    mkdir -p "$OUTPUT_TEMP_DIR"
    
    # Copy .vhd extracted files to output, preserving their structure
    echo -e "${GREEN}Copying .vhd files to output (preserving directory structure)...${NC}"
    if [ -d "$VHD_EXTRACT_DIR" ] && [ "$(ls -A "$VHD_EXTRACT_DIR" 2>/dev/null)" ]; then
        if command -v rsync &> /dev/null; then
            rsync -a "$VHD_EXTRACT_DIR/" "$OUTPUT_TEMP_DIR/"
        else
            cp -r "$VHD_EXTRACT_DIR"/* "$OUTPUT_TEMP_DIR/" 2>/dev/null || true
        fi
    fi
    
    # Copy other files from source to output root (excluding .vhd)
    echo -e "${GREEN}Collecting other files (excluding .vhd) to zip root...${NC}"
    cd "$TEMP_DIR"
    find . -type f ! -iname "*.vhd" ! -path "./vhd_extracted/*" ! -path "./output/*" | while IFS= read -r file; do
        # Get just the filename (basename) to place at root
        filename=$(basename "$file")
        # Handle filename conflicts by adding parent directory name if needed
        if [ -f "$OUTPUT_TEMP_DIR/$filename" ]; then
            # If file already exists, prefix with parent dir name
            parent_dir=$(basename "$(dirname "$file")")
            if [ "$parent_dir" != "." ]; then
                filename="${parent_dir}_${filename}"
            fi
        fi
        cp "$file" "$OUTPUT_TEMP_DIR/$filename"
    done
    
    # Add AUTOBOOT.DBP from source zip directory to output root (only if not already in source zip)
    if [ ! -f "$OUTPUT_TEMP_DIR/AUTOBOOT.DBP" ]; then
        local SOURCE_DIR=$(dirname "$SOURCE_ZIP")
        local AUTOBOOT_FILE="$SOURCE_DIR/AUTOBOOT.DBP"
        if [ -f "$AUTOBOOT_FILE" ]; then
            echo -e "${GREEN}Adding AUTOBOOT.DBP from source directory to zip root...${NC}"
            cp "$AUTOBOOT_FILE" "$OUTPUT_TEMP_DIR/AUTOBOOT.DBP"
        else
            echo -e "${YELLOW}Note: AUTOBOOT.DBP not found in source directory: $SOURCE_DIR${NC}"
        fi
    else
        echo -e "${GREEN}AUTOBOOT.DBP already present in source zip, keeping it${NC}"
    fi
    
    # Create output zip
    echo -e "${GREEN}Creating output zip: $OUTPUT_ZIP${NC}"
    
    # Remove output zip if it exists
    [ -f "$OUTPUT_ZIP" ] && rm -f "$OUTPUT_ZIP"
    
    # Create zip from output directory, preserving directory structure
    cd "$OUTPUT_TEMP_DIR"
    if ! zip -r "$OUTPUT_ZIP" . -q; then
        echo -e "${RED}Error: Failed to create output zip${NC}" >&2
        rm -rf "$TEMP_DIR" "$MOUNT_POINT"
        local_cleanup
        return 1
    fi
    
    OUTPUT_CREATED=true
    
    echo -e "${GREEN}Success! Output zip created: $OUTPUT_ZIP${NC}"
    
    # Count files in output zip for verification
    local FILE_COUNT=$(unzip -l "$OUTPUT_ZIP" | tail -n 1 | awk '{print $2}')
    echo -e "${GREEN}Output zip contains $FILE_COUNT files${NC}"
    
    # Cleanup temp directory for this zip
    rm -rf "$TEMP_DIR" "$MOUNT_POINT"
    
    # Return success
    return 0
}

# Process each zip file
PROCESSED=0
FAILED=0
SKIPPED=0

# Create error log file in the same directory as the script
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ERROR_LOG="$SCRIPT_DIR/extract_errors.log"
# Clear/create log file with header
echo "VHD Extract Error Log - $(date '+%Y-%m-%d %H:%M:%S')" > "$ERROR_LOG"
echo "========================================" >> "$ERROR_LOG"
echo "" >> "$ERROR_LOG"

# Use process substitution to avoid subshell issues with variable updates
while IFS= read -r SOURCE_ZIP; do
    # Skip empty lines
    [ -z "$SOURCE_ZIP" ] && continue
    
    # Get output zip name (same as source, in output directory)
    ZIP_BASENAME=$(basename "$SOURCE_ZIP")
    OUTPUT_ZIP="$OUTPUT_DIR_ABS/$ZIP_BASENAME"
    
    # Check if output zip already exists
    if [ -f "$OUTPUT_ZIP" ]; then
        # Compare file sizes - only reprocess if output is more than 10MB smaller
        INPUT_SIZE=$(stat -f%z "$SOURCE_ZIP" 2>/dev/null || stat -c%s "$SOURCE_ZIP" 2>/dev/null)
        OUTPUT_SIZE=$(stat -f%z "$OUTPUT_ZIP" 2>/dev/null || stat -c%s "$OUTPUT_ZIP" 2>/dev/null)
        SIZE_DIFF_THRESHOLD=$((10 * 1024 * 1024))  # 10MB in bytes
        
        if [ -n "$INPUT_SIZE" ] && [ -n "$OUTPUT_SIZE" ]; then
            SIZE_DIFF=$((INPUT_SIZE - OUTPUT_SIZE))
            if [ "$SIZE_DIFF" -gt "$SIZE_DIFF_THRESHOLD" ]; then
                echo -e "${YELLOW}Output zip exists but is more than 10MB smaller than input (diff: ${SIZE_DIFF} bytes), deleting and reprocessing...${NC}"
                rm -f "$OUTPUT_ZIP"
            else
                echo -e "${YELLOW}Skipping $ZIP_BASENAME - output already exists and is valid${NC}"
                SKIPPED=$((SKIPPED + 1))
                continue
            fi
        else
            # If we can't get sizes, skip to be safe
            echo -e "${YELLOW}Skipping $ZIP_BASENAME - output already exists${NC}"
            SKIPPED=$((SKIPPED + 1))
            continue
        fi
    fi
    
    # Temporarily disable exit on error for the function call
    set +e
    if process_zip_file "$SOURCE_ZIP" "$OUTPUT_ZIP"; then
        PROCESSED=$((PROCESSED + 1))
    else
        FAILED=$((FAILED + 1))
        echo -e "${RED}Failed to process: $ZIP_BASENAME${NC}"
        # Log error to file
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] FAILED: $ZIP_BASENAME" >> "$ERROR_LOG"
        echo "  Source: $SOURCE_ZIP" >> "$ERROR_LOG"
        echo "  Output: $OUTPUT_ZIP" >> "$ERROR_LOG"
        echo "" >> "$ERROR_LOG"
    fi
    set -e
done < <(echo "$ZIP_FILES")

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Processing complete!${NC}"
echo -e "${GREEN}Successfully processed: $PROCESSED${NC}"
if [ $SKIPPED -gt 0 ]; then
    echo -e "${YELLOW}Skipped (already exist): $SKIPPED${NC}"
fi
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Failed: $FAILED${NC}"
    echo -e "${YELLOW}Error log saved to: $ERROR_LOG${NC}"
fi
echo -e "${GREEN}========================================${NC}"

# Add summary to error log
if [ $FAILED -gt 0 ]; then
    echo "" >> "$ERROR_LOG"
    echo "========================================" >> "$ERROR_LOG"
    echo "Summary: $FAILED failed, $PROCESSED processed, $SKIPPED skipped" >> "$ERROR_LOG"
fi

# Disable cleanup since we're exiting successfully
CLEANUP_ON_EXIT=false
