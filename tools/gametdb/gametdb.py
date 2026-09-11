#!/usr/bin/env python3
"""
Shared pieces for the GameTDB tools: system/language tables, the art mirror
layout, and the priority rules that decide which language's artwork a game gets.

GameTDB keys its artwork by game id *and* language, e.g.

    https://art.gametdb.com/switch/coverHQ/US/A224A.jpg
                            ^system  ^type  ^lang ^id

A game usually has art in only a handful of languages, so every media lookup
walks a per-game priority list and takes the first language that actually has
the file. US comes first, then EN, then whatever the game's own region and
language list suggest, then the rest as a last resort.
"""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Where the unzipped GameTDB artwork lives, and the URL the application serves
# it under. Both are the same string, so a value stored in the JSON database is
# at once a browser-usable URL and a repository-relative file path.
MEDIA_ROOT_REL = os.path.join('var', 'db', 'custom', 'medias', 'gametdb')
MEDIA_ROOT = os.path.join(BASE_DIR, MEDIA_ROOT_REL)
MEDIA_URL_ROOT = '/var/db/custom/medias/gametdb'

CUSTOM_DB_DIR = os.path.join(BASE_DIR, 'var', 'db', 'custom')

# GameTDB's own site path per system, used to build the game's page URL.
SITE_SECTION = {
    'switch': 'Switch',
    '3ds': '3DS',
    'wii': 'Wii',
    'wiiu': 'WiiU',
    'ds': 'DS',
    'ps3': 'PS3',
    'gc': 'GC',
}

# Art types, in the order they are tried for each custom-database media field.
# The extension is fixed per type: GameTDB serves covers as JPEG and the
# cartridge/label/3D-box renders as transparent PNG.
MEDIA_FIELDS = {
    # The 2D front cover. coverHQ is 1166x1888; coverM (352x570) is the best
    # the downloadable zips offer, so it stands in when no HQ scan exists.
    'boxfront': [('coverHQ', '.jpg'), ('coverM', '.jpg'), ('cover', '.jpg')],
    # The full wrap -- back, spine and front in one image. GameTDB has no
    # separate back cover, so this is what the boxback field gets.
    'boxback': [('coverfullHQ', '.jpg'), ('coverfull', '.jpg')],
    # The game card itself, then the bare label as a fallback.
    'cartridge': [('cart', '.png'), ('label', '.png')],
}

# Every art type the tools know how to mirror, with the extension it uses.
ART_TYPES = {
    'coverHQ': '.jpg',
    'coverfullHQ': '.jpg',
    'coverM': '.jpg',
    'cover': '.jpg',
    'coverfull': '.jpg',
    'cart': '.png',
    'label': '.png',
    'box': '.png',
}

# Art types GameTDB publishes as downloadable zip archives. Everything else has
# to be fetched one file at a time.
ZIP_TYPES = ('coverM', 'cart', 'label', 'box')

# Language directories used by art.gametdb.com, most-generally-useful first.
# This doubles as the last-resort fallback order when a game's own languages
# turn up nothing.
ART_LANGS = [
    'US', 'EN', 'JA', 'FR', 'DE', 'ES', 'IT', 'NL', 'PT', 'RU', 'KO', 'ZH',
    'AU', 'NZ', 'CA', 'MX', 'CH', 'SE', 'DK', 'NO', 'FI', 'AE', 'SA', 'ZA',
]

# GameTDB's <languages> codes mapped onto art directories. Codes with no
# directory of their own (PL, HU, TR, GR, CS) are deliberately absent.
LANG_TO_ART = {
    'EN': 'EN', 'JA': 'JA', 'FR': 'FR', 'DE': 'DE', 'ES': 'ES', 'IT': 'IT',
    'NL': 'NL', 'PT': 'PT', 'RU': 'RU', 'KO': 'KO', 'SE': 'SE', 'DK': 'DK',
    'NO': 'NO', 'FI': 'FI', 'ZHCN': 'ZH', 'ZHTW': 'ZH', 'ZH': 'ZH', 'AR': 'AE',
}

# <region> is spelled differently per system -- Switch uses USA/EUR/JPN, the
# 3DS uses the NTSC/PAL names -- so both vocabularies are mapped here.
REGION_TO_ART = {
    'USA': ['US', 'CA', 'MX'],
    'NTSC-U': ['US', 'CA', 'MX'],
    'EUR': ['EN', 'FR', 'DE', 'ES', 'IT', 'NL', 'PT', 'SE', 'DK', 'NO', 'FI', 'RU', 'CH'],
    'PAL': ['EN', 'FR', 'DE', 'ES', 'IT', 'NL', 'PT', 'SE', 'DK', 'NO', 'FI', 'RU', 'CH'],
    'PAL-R': ['RU', 'EN'],
    'JPN': ['JA'],
    'NTSC-J': ['JA'],
    'KOR': ['KO'],
    'NTSC-K': ['KO'],
    'CHN': ['ZH'],
    'TWN': ['ZH'],
    'NTSC-T': ['ZH'],
    'AUS': ['AU', 'NZ'],
    'ALL': [],
}


def system_from_xml(path):
    """GameTDB system key for a database file, e.g. switchtdb.xml -> switch."""
    name = os.path.basename(path).lower()
    for suffix in ('tdb.xml', '.xml'):
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return name


def art_url(system, art_type, lang, game_id):
    """Remote URL of one artwork file on art.gametdb.com."""
    ext = ART_TYPES.get(art_type, '.jpg')
    return f"https://art.gametdb.com/{system}/{art_type}/{lang}/{game_id}{ext}"


def art_path(system, art_type, lang, game_id):
    """Local path of one artwork file inside the mirror."""
    ext = ART_TYPES.get(art_type, '.jpg')
    return os.path.join(MEDIA_ROOT, system, art_type, lang, game_id + ext)


def art_media_url(system, art_type, lang, game_id):
    """The value stored in the JSON database for one mirrored artwork file."""
    ext = ART_TYPES.get(art_type, '.jpg')
    return f"{MEDIA_URL_ROOT}/{system}/{art_type}/{lang}/{game_id}{ext}"


def language_priority(region, languages):
    """Languages to try for one game, best first.

    US first and EN second because those covers carry the widest reach of
    English titles, then the languages implied by the game's region, then the
    ones it actually ships with, and finally everything else -- a Japanese
    cover beats no cover at all.
    """
    ordered = ['US', 'EN']

    for part in (region or '').split(','):
        for lang in REGION_TO_ART.get(part.strip().upper(), []):
            if lang not in ordered:
                ordered.append(lang)

    for part in (languages or '').split(','):
        lang = LANG_TO_ART.get(part.strip().upper())
        if lang and lang not in ordered:
            ordered.append(lang)

    for lang in ART_LANGS:
        if lang not in ordered:
            ordered.append(lang)

    return ordered
