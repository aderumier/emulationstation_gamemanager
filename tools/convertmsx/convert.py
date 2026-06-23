#!/usr/bin/env python3
"""
Rename MSX zip ROMs using SHA1 lookup against file_hash_db.yaml.
Updates gamelist.xml and renames associated media files.

Usage:
  python convert.py [roms_dir] [--gamelist PATH] [--dry-run]

Defaults:
  roms_dir  = <project_root>/roms/msx1
  gamelist  = <roms_dir>/gamelist.xml
"""

import argparse
import hashlib
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

try:
    import yaml
except ImportError:
    print("Error: PyYAML required. Run: pip install pyyaml")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
DB_PATH = SCRIPT_DIR / "file_hash_db.yaml"

# Full language name (lowercase) → no-intro short code
LANGUAGE_CODES = {
    "english": "En",
    "japanese": "Ja",
    "french": "Fr",
    "german": "De",
    "deutsch": "De",
    "spanish": "Es",
    "castelland": "Es",
    "castellano": "Es",
    "dutch": "Nl",
    "italian": "It",
    "korean": "Ko",
    "portuguese": "Pt",
    "portugese": "Pt",
    "arabic": "Ar",
    "arab": "Ar",
    "russian": "Ru",
    "swedish": "Sv",
    "norwegian": "No",
    "danish": "Da",
    "finnish": "Fi",
    "polish": "Pl",
    "catalan": "Ca",
    "basque": "Eu",
    "galician": "Gl",
    "tagalog": "Tl",
    "chinese": "Zh",
}

# XML fields that may contain media file paths (besides <path>)
MEDIA_FIELDS = [
    "image", "wheel", "boxart", "cartridge", "mix", "thumbnail",
    "marquee", "video", "fanart", "titleshot", "manual", "boxback", "extra1",
]


# ---------------------------------------------------------------------------
# Language parsing
# ---------------------------------------------------------------------------

def parse_language(lang_str: str) -> str:
    """Convert a Language field value to a no-intro short code string."""
    if not lang_str:
        return ""
    lang_str = lang_str.strip()
    if lang_str.lower() in ("none", ""):
        return ""

    # Split on common separators: , / & "and"
    parts = re.split(r'[,/&]+', lang_str)
    codes: list[str] = []
    for part in parts:
        part = part.strip()
        # Drop parenthetical notes like "(title in Japanese)"
        part = re.sub(r'\s*\(.*?\)', '', part).strip()
        # Drop "partially"
        part = re.sub(r'^partially\s+', '', part, flags=re.IGNORECASE).strip()
        # Split remaining on "and"
        for token in re.split(r'\s+and\s+', part, flags=re.IGNORECASE):
            token = token.strip().lower()
            if token:
                code = LANGUAGE_CODES.get(token)
                if code and code not in codes:
                    codes.append(code)

    return ",".join(c for c in codes if c)


# ---------------------------------------------------------------------------
# YAML database loading
# ---------------------------------------------------------------------------

def load_db(db_path: Path) -> dict[str, dict]:
    """Return sha1 (lowercase) → entry dict from the YAML database."""
    with open(db_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    index: dict[str, dict] = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        files = item.get("Files")
        if not isinstance(files, list):
            continue
        for entry in files:
            if not isinstance(entry, dict):
                continue
            if str(entry.get("Genre") or "").strip().lower() == "bad dump":
                continue
            sha1 = entry.get("sha1", "")
            if sha1:
                index[sha1.lower().strip()] = entry
    return index


# ---------------------------------------------------------------------------
# ZIP SHA1 computation
# ---------------------------------------------------------------------------

def zip_sha1s(zip_path: Path) -> list[str]:
    """Return SHA1 hashes of every file inside a zip archive."""
    result = []
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                with zf.open(info) as f:
                    result.append(hashlib.sha1(f.read()).hexdigest())
    except Exception as exc:
        print(f"  Warning: cannot read {zip_path.name}: {exc}")
    return result


# ---------------------------------------------------------------------------
# New filename construction
# ---------------------------------------------------------------------------

def extract_brackets(longname: str) -> list[str]:
    """Return all [xxx] tokens from a Longname string."""
    return re.findall(r'\[[^\]]+\]', longname or "")


def clean_longname(longname: str) -> str:
    """Strip file extension, all (...) and [...] blocks from a Longname, returning the bare title."""
    name = Path(longname).stem          # drop .rom / .sg / .sms / etc.
    name = re.sub(r'\s*\([^)]*\)', '', name)   # remove all (...)
    name = re.sub(r'\s*\[[^\]]*\]', '', name)  # remove all [...]
    return name.strip()


def sanitize_filename(name: str) -> str:
    """Remove characters that are problematic in filenames."""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    return name.strip(". ")


def build_new_name(entry: dict, add_developer: bool) -> str | None:
    """Build the new filename stem for a matched DB entry."""

    def field(key: str) -> str:
        return str(entry.get(key) or "").strip()

    longname = field("Longname")
    if not longname:
        return None

    name = clean_longname(longname)
    if not name:
        return None

    if add_developer:
        dev = field("Developer")
        if dev:
            name += f" ({dev})"

    country = field("Country")
    if country:
        name += f" ({country})"

    lang_code = parse_language(field("Language"))
    if lang_code:
        name += f" ({lang_code})"

    # Version/extra tags from Longname  e.g. [2.4], [MSX2]
    for bracket in extract_brackets(field("Longname")):
        name += f" {bracket}"

    return sanitize_filename(name)


# ---------------------------------------------------------------------------
# Gamelist XML helpers
# ---------------------------------------------------------------------------

def load_gamelist(path: Path):
    tree = ET.parse(str(path))
    return tree, tree.getroot()


def save_gamelist(tree: ET.ElementTree, path: Path) -> None:
    try:
        ET.indent(tree, space="\t")
    except AttributeError:
        pass  # Python < 3.9 — skip re-indentation

    xml_bytes = ET.tostring(tree.getroot(), encoding="unicode")
    with open(path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0"?>\n')
        f.write(xml_bytes)
        f.write("\n")


def gamelist_stem_map(root: ET.Element) -> dict[str, ET.Element]:
    """Build stem → <game> element mapping from <path> entries."""
    mapping: dict[str, ET.Element] = {}
    for game in root.findall("game"):
        path_elem = game.find("path")
        if path_elem is not None and path_elem.text:
            stem = Path(path_elem.text).stem
            mapping[stem] = game
    return mapping


def update_game_paths(game: ET.Element, old_stem: str, new_stem: str) -> None:
    """Rewrite path + all media path fields in a <game> element."""
    for field in ["path"] + MEDIA_FIELDS:
        elem = game.find(field)
        if elem is None or not elem.text:
            continue
        text = elem.text
        fname = Path(text).name          # e.g. "1942 (Japan).png"
        fstem = Path(fname).stem         # e.g. "1942 (Japan)"
        if fstem == old_stem:
            new_fname = new_stem + Path(fname).suffix
            # Preserve the directory prefix (e.g. "./media/images/")
            prefix = text[: -len(fname)]
            elem.text = prefix + new_fname


# ---------------------------------------------------------------------------
# Media file renaming
# ---------------------------------------------------------------------------

def rename_media(media_dir: Path, old_stem: str, new_stem: str,
                 dry_run: bool) -> list[tuple[Path, Path]]:
    """Rename every file whose stem matches old_stem in all sub-dirs of media_dir."""
    ops: list[tuple[Path, Path]] = []
    if not media_dir.is_dir():
        return ops
    for subdir in media_dir.iterdir():
        if not subdir.is_dir():
            continue
        for f in subdir.iterdir():
            if f.stem == old_stem:
                new_path = f.parent / (new_stem + f.suffix)
                ops.append((f, new_path))
                if not dry_run:
                    f.rename(new_path)
    return ops


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    default_roms = str(SCRIPT_DIR.parent.parent / "roms" / "msx1")

    parser = argparse.ArgumentParser(
        description="Rename MSX zip ROMs by SHA1 and update gamelist.xml"
    )
    parser.add_argument(
        "roms_dir", nargs="?", default=default_roms,
        help=f"Path to the roms directory (default: {default_roms})"
    )
    parser.add_argument(
        "--gamelist", default=None,
        help="Path to gamelist.xml (default: <roms_dir>/gamelist.xml)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview changes without modifying anything"
    )
    args = parser.parse_args()

    roms_dir = Path(args.roms_dir)
    gamelist_path = Path(args.gamelist) if args.gamelist else roms_dir / "gamelist.xml"

    if not roms_dir.is_dir():
        print(f"Error: roms directory not found: {roms_dir}")
        sys.exit(1)

    # Load database
    print(f"Loading database: {DB_PATH}")
    sha1_index = load_db(DB_PATH)
    print(f"  {len(sha1_index)} entries loaded")

    # Collect zip files
    zip_files = sorted(
        zp for zp in roms_dir.rglob("*.zip")
        if "media" not in zp.relative_to(roms_dir).parts
    )
    print(f"Found {len(zip_files)} zip files in {roms_dir} (including subfolders)")
    if not zip_files:
        print("Nothing to do.")
        return

    # --- Pass 1: match each zip to a DB entry via SHA1 ---
    matches: dict[Path, dict] = {}
    unmatched: list[Path] = []
    for zp in zip_files:
        matched_entry = None
        for sha1 in zip_sha1s(zp):
            entry = sha1_index.get(sha1)
            if entry:
                matched_entry = entry
                break
        if matched_entry:
            matches[zp] = matched_entry
        else:
            unmatched.append(zp)

    print(f"Matched: {len(matches)}  |  Unmatched: {len(unmatched)}")
    if unmatched:
        print("Unmatched files:")
        for zp in unmatched:
            print(f"  {zp.name}")

    # --- Detect titles that have more than one distinct developer ---
    title_devs: dict[str, set[str]] = defaultdict(set)
    for entry in matches.values():
        title_key = clean_longname(str(entry.get("Longname") or ""))
        dev = str(entry.get("Developer") or "").strip()
        if title_key:
            title_devs[title_key].add(dev)

    # --- Build rename plan: old_stem → new_stem ---
    plan: dict[Path, str] = {}
    # Track used stems per directory to avoid intra-dir collisions
    used_stems_by_dir: dict[Path, set[str]] = defaultdict(set)
    for zp in zip_files:
        used_stems_by_dir[zp.parent].add(zp.stem)

    for zp, entry in matches.items():
        title_key = clean_longname(str(entry.get("Longname") or ""))
        needs_dev = len(title_devs.get(title_key, set())) > 1
        new_stem = build_new_name(entry, needs_dev)
        if new_stem is None:
            print(f"  Warning: could not build name for {zp.name}, skipping")
            continue
        if new_stem == zp.stem:
            continue  # already correctly named

        # Collision guard (scoped to the same directory)
        dir_stems = used_stems_by_dir[zp.parent]
        if new_stem in dir_stems and zp.stem != new_stem:
            print(f"  Warning: collision for '{new_stem}', keeping original name for {zp.name}")
            continue

        plan[zp] = new_stem
        dir_stems.discard(zp.stem)
        dir_stems.add(new_stem)

    # --- Handle unmatched *.rom.zip: strip the ".rom" suffix from the stem ---
    for zp in unmatched:
        if zp.stem.lower().endswith(".rom"):
            new_stem = zp.stem[:-4]  # drop trailing ".rom"
            dir_stems = used_stems_by_dir[zp.parent]
            if new_stem in dir_stems and zp.stem != new_stem:
                print(f"  Warning: collision for '{new_stem}', keeping original name for {zp.name}")
                continue
            if new_stem != zp.stem:
                plan[zp] = new_stem
                dir_stems.discard(zp.stem)
                dir_stems.add(new_stem)

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Will rename {len(plan)} file(s):")

    if not plan:
        print("  (nothing to rename)")
        return

    for zp, new_stem in sorted(plan.items()):
        print(f"  {zp.name}")
        print(f"    → {new_stem}.zip")

    if args.dry_run:
        return

    # --- Load gamelist (optional) ---
    tree = root = None
    stem_map: dict[str, ET.Element] = {}
    if gamelist_path.is_file():
        try:
            tree, root = load_gamelist(gamelist_path)
            stem_map = gamelist_stem_map(root)
            print(f"\nLoaded gamelist: {gamelist_path} ({len(stem_map)} entries)")
        except Exception as exc:
            print(f"Warning: could not parse gamelist.xml: {exc}")

    media_dir = gamelist_path.parent / "media"

    # --- Execute renames ---
    print()
    for zp, new_stem in sorted(plan.items()):
        old_stem = zp.stem
        new_zip = zp.parent / f"{new_stem}.zip"

        print(f"Renaming zip:  {zp.name}")
        print(f"           →   {new_zip.name}")
        zp.rename(new_zip)

        # Update gamelist entry
        if root is not None and old_stem in stem_map:
            update_game_paths(stem_map[old_stem], old_stem, new_stem)

        # Rename media files
        ops = rename_media(media_dir, old_stem, new_stem, dry_run=False)
        for old_f, new_f in ops:
            print(f"  media: {old_f.parent.name}/{old_f.name} → {new_f.name}")

    # Save updated gamelist
    if tree is not None and plan:
        save_gamelist(tree, gamelist_path)
        print(f"\nSaved gamelist: {gamelist_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
