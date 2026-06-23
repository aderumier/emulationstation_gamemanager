#!/usr/bin/env python3
"""
Delete media files for a given system and media type whose image dimensions
exceed a given pixel size.

Media live under:  <roms_root>/<system>/media/<directory>/
where <directory> is resolved from config.json media_fields[<type>].directory
(e.g. type "fanart" -> directory "fanarts").

Examples:
    # Dry run: list fanart images taller than 800px for the 'nes' system
    python3 tools/delete_oversized_medias.py --system nes --type fanart --max-height 800

    # Actually delete them
    python3 tools/delete_oversized_medias.py --system nes --type fanart --max-height 800 --delete

    # Delete fanart wider than 1920px OR taller than 1080px
    python3 tools/delete_oversized_medias.py --system nes --type fanart \
        --max-width 1920 --max-height 1080 --delete
"""
import sys
import os
import json
import argparse
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow is required (pip install Pillow)", file=sys.stderr)
    sys.exit(1)

# Resolve project root (parent of this tools/ directory) so the script can be
# run from anywhere.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PROJECT_ROOT / "var" / "config" / "config.json"


def load_config(config_path):
    if not config_path.exists():
        print(f"ERROR: config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_media_dir(config, system, media_type):
    """Return the absolute Path to <roms_root>/<system>/media/<directory>."""
    roms_root = config.get("roms_root_directory")
    if not roms_root:
        print("ERROR: 'roms_root_directory' missing from config", file=sys.stderr)
        sys.exit(1)

    media_fields = config.get("media_fields", {})
    field_cfg = media_fields.get(media_type)
    if field_cfg is None:
        valid = ", ".join(sorted(media_fields.keys()))
        print(f"ERROR: unknown media type '{media_type}'. Valid types: {valid}",
              file=sys.stderr)
        sys.exit(1)

    # directory may be specified in config; fall back to the type name itself.
    if isinstance(field_cfg, dict):
        directory = field_cfg.get("directory", media_type)
    else:
        directory = media_type

    return Path(roms_root) / system / "media" / directory


def main():
    parser = argparse.ArgumentParser(
        description="Delete media files for a system/type whose dimensions exceed a size.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--system", required=True,
                        help="System name (e.g. nes, snes, mame)")
    parser.add_argument("--type", required=True, dest="media_type",
                        help="Media type / field name (e.g. fanart, boxart, image)")
    parser.add_argument("--max-width", type=int, default=None,
                        help="Delete images whose width is strictly greater than this")
    parser.add_argument("--max-height", type=int, default=None,
                        help="Delete images whose height is strictly greater than this")
    parser.add_argument("--delete", action="store_true",
                        help="Actually delete files. Without this flag the script "
                             "only reports what would be deleted (dry run).")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG,
                        help=f"Path to config.json (default: {DEFAULT_CONFIG})")
    args = parser.parse_args()

    if args.max_width is None and args.max_height is None:
        parser.error("at least one of --max-width / --max-height is required")

    config = load_config(args.config)
    media_dir = resolve_media_dir(config, args.system, args.media_type)

    if not media_dir.is_dir():
        print(f"ERROR: media directory does not exist: {media_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning: {media_dir}")
    limits = []
    if args.max_width is not None:
        limits.append(f"width > {args.max_width}")
    if args.max_height is not None:
        limits.append(f"height > {args.max_height}")
    print(f"Condition: {' OR '.join(limits)}")
    print(f"Mode: {'DELETE' if args.delete else 'DRY RUN (use --delete to apply)'}")
    print("-" * 60)

    scanned = 0
    matched = 0
    deleted = 0
    errors = 0
    freed_bytes = 0

    for entry in sorted(media_dir.iterdir()):
        if not entry.is_file():
            continue
        # Skip hidden/system files.
        if entry.name.startswith("."):
            continue

        scanned += 1
        try:
            with Image.open(entry) as img:
                width, height = img.size
        except Exception as e:
            # Not an image / unreadable — leave it alone.
            print(f"  SKIP (not an image?): {entry.name} ({e})")
            errors += 1
            continue

        too_wide = args.max_width is not None and width > args.max_width
        too_tall = args.max_height is not None and height > args.max_height
        if not (too_wide or too_tall):
            continue

        matched += 1
        size_bytes = entry.stat().st_size
        action = "DELETE" if args.delete else "WOULD DELETE"
        print(f"  {action}: {entry.name} ({width}x{height}, {size_bytes / 1024:.0f} KB)")

        if args.delete:
            try:
                entry.unlink()
                deleted += 1
                freed_bytes += size_bytes
            except Exception as e:
                print(f"    ERROR deleting {entry.name}: {e}", file=sys.stderr)
                errors += 1
        else:
            freed_bytes += size_bytes

    print("-" * 60)
    print(f"Scanned: {scanned} file(s)")
    print(f"Matched: {matched} file(s)")
    if args.delete:
        print(f"Deleted: {deleted} file(s), freed {freed_bytes / (1024 * 1024):.2f} MB")
    else:
        print(f"Would delete: {matched} file(s), ~{freed_bytes / (1024 * 1024):.2f} MB")
    if errors:
        print(f"Errors/skipped: {errors}")


if __name__ == "__main__":
    main()
