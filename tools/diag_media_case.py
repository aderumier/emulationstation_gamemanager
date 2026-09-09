#!/usr/bin/env python3
"""Diagnose why clean_missing_medias does not fix a case mismatch.

Usage:  python3 tools/diag_media_case.py <system_name> [substring of game name/path]

Prints, for each matching game: the gamelist <path>, each media field, the raw
os.listdir() entries of the media directory (repr, so case/oddities are visible),
and the decision clean_missing_medias would take.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import xml.etree.ElementTree as ET

CONFIG = json.load(open('var/config/config.json'))
ROMS_FOLDER = CONFIG['roms_root_directory']
GAMELISTS_FOLDER = 'var/gamelists'
MEDIA_FIELDS = CONFIG.get('media_fields', {})

system_name = sys.argv[1]
needle = sys.argv[2].lower() if len(sys.argv) > 2 else ''

gamelist_path = os.path.join(GAMELISTS_FOLDER, system_name, 'gamelist.xml')
system_path = os.path.join(ROMS_FOLDER, system_name)
print(f"gamelist : {gamelist_path}")
print(f"system   : {system_path}\n")

root = ET.parse(gamelist_path).getroot()
listings = {}


def listing_for(directory):
    if directory not in listings:
        try:
            listings[directory] = os.listdir(directory)
        except OSError as e:
            listings[directory] = e
    return listings[directory]


for game in root.findall('game'):
    fields = {c.tag: (c.text or '').strip() for c in game}
    rom_path = fields.get('path', '')
    name = fields.get('name', '')
    if needle and needle not in rom_path.lower() and needle not in name.lower():
        continue

    rom_stem = os.path.splitext(os.path.basename(rom_path))[0]
    print(f"=== {name}")
    print(f"  <path>    {rom_path!r}")
    print(f"  rom stem  {rom_stem!r}")

    for field in MEDIA_FIELDS:
        media_path = fields.get(field, '')
        if not media_path:
            continue
        np = media_path.removeprefix('./')
        if np.startswith(os.sep):
            full = np
        elif np.startswith(system_name):
            full = os.path.join(ROMS_FOLDER, np)
        else:
            full = os.path.join(system_path, np)

        media_dir = os.path.dirname(full)
        ref = os.path.basename(full)
        entries = listing_for(media_dir)
        print(f"  <{field}> {media_path!r}")
        if isinstance(entries, OSError):
            print(f"      !! listdir({media_dir}) failed: {entries}")
            continue

        real = {n.lower(): n for n in entries}
        actual = real.get(ref.lower())
        matches = [n for n in entries if n.lower() == ref.lower()]
        print(f"      os.path.exists()   : {os.path.exists(full)}")
        print(f"      listdir hits       : {matches!r}")
        if not actual:
            print("      => would be CLEANED (no case-insensitive match in listing)")
            continue
        ext = os.path.splitext(actual)[1]
        correct = f"{rom_stem}{ext}" if rom_stem else actual
        print(f"      on disk            : {actual!r}")
        print(f"      canonical (ROM)    : {correct!r}")
        if actual == correct:
            print("      => file NOT renamed (already matches ROM name)")
        else:
            print(f"      => would RENAME {actual!r} -> {correct!r}")
        new_media_path = os.path.join(os.path.dirname(media_path), correct)
        if new_media_path != media_path:
            print(f"      => would UPDATE gamelist: {media_path!r} -> {new_media_path!r}")
    print()
