#!/usr/bin/env python3
"""
Convert GameTDB's XML databases into the custom JSON databases the scrapper
reads from var/db/custom/.

One XML file becomes one database: switchtdb.xml -> gametdb_switch.json,
3dstdb.xml -> gametdb_3ds.json, keyed by the GameTDB game id.

Media links point at the local artwork mirror under
var/db/custom/medias/gametdb/, which fetch_art.py fills. Only files that are
actually present in the mirror are written, so the database never offers an
image that cannot be shown or downloaded. Run fetch_art.py first, or the games
come out with text fields only.

Usage:
  python convert.py                     # convert every *tdb.xml in this directory
  python convert.py switchtdb.xml       # convert one file
  python convert.py --output-dir DIR    # write somewhere other than var/db/custom
"""

import argparse
import json
import os
import sys
from xml.etree import ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gametdb import (
    CUSTOM_DB_DIR,
    MEDIA_FIELDS,
    MEDIA_ROOT,
    SITE_SECTION,
    art_media_url,
    language_priority,
    system_from_xml,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Genre names GameTDB writes in lower case that should not simply be
# title-cased ("action rpg" must not become "Action Rpg").
GENRE_CASE = {
    'action rpg': 'Action RPG',
    'strategy rpg': 'Strategy RPG',
    'role-playing': 'Role-Playing',
    'first-person shooter': 'First-Person Shooter',
    'third-person shooter': 'Third-Person Shooter',
    'point-and-click': 'Point-and-Click',
    '2d fighting': '2D Fighting',
    '3d fighting': '3D Fighting',
    '2d platformer': '2D Platformer',
    '3d platformer': '3D Platformer',
    'sci-fi': 'Sci-Fi',
    'real-time strategy': 'Real-Time Strategy',
    'turn-based strategy': 'Turn-Based Strategy',
    'off-road racing': 'Off-Road Racing',
    "beat 'em up": "Beat 'em Up",
    "shoot 'em up": "Shoot 'em Up",
    'run and gun': 'Run and Gun',
}

# Region-specific release dates, tried in this order when the generic <date>
# element carries no year.
DATE_FALLBACKS = ('date_USA', 'date_EUR', 'date_JPN', 'date_KOR')


def text_of(element, tag):
    """Stripped text of a child element, or '' when absent or empty."""
    value = element.findtext(tag)
    return value.strip() if value else ''


def locales(game):
    """{language code: (title, synopsis)} for one game."""
    found = {}
    for locale in game.findall('locale'):
        lang = (locale.get('lang') or '').upper()
        if not lang:
            continue
        found[lang] = (text_of(locale, 'title'), text_of(locale, 'synopsis'))
    return found


def locale_order(game, available):
    """Locale codes to read a title or synopsis from, best first."""
    order = ['EN']
    for part in (text_of(game, 'languages')).split(','):
        part = part.strip().upper()
        if part and part not in order:
            order.append(part)
    for lang in available:
        if lang not in order:
            order.append(lang)
    return order


def game_name(game, available):
    """Clean display title.

    The <game name> attribute carries a language suffix -- "Celeste (EN,FR,DE)"
    -- which would only get in the way of name matching, so the locale title is
    preferred and the attribute is just a fallback.
    """
    for lang in locale_order(game, available):
        title = available.get(lang, ('', ''))[0]
        if title:
            return title
    return (game.get('name') or '').strip()


def game_description(game, available):
    """Synopsis in the most useful language available."""
    for lang in locale_order(game, available):
        synopsis = available.get(lang, ('', ''))[1]
        if synopsis:
            return synopsis
    return ''


def release_date(game):
    """Release date as YYYY-MM-DD, YYYY-MM or YYYY, whichever is known.

    All three parse unambiguously in the application, unlike the day-first
    formats some other custom databases use.
    """
    candidates = [game.find('date')]
    candidates += [game.find(tag) for tag in DATE_FALLBACKS]

    for date in candidates:
        if date is None:
            continue
        year = (date.get('year') or '').strip()
        if not year.isdigit():
            continue
        month = (date.get('month') or '').strip()
        day = (date.get('day') or '').strip()
        if not month.isdigit():
            return year
        if not day.isdigit():
            return f"{int(year):04d}-{int(month):02d}"
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    return ''


def players(game):
    """Player count as a range string, e.g. "1" or "1-4"."""
    element = game.find('input')
    if element is None:
        return ''
    try:
        count = int(element.get('players') or 0)
    except ValueError:
        return ''
    if count < 1:
        return ''
    return '1' if count == 1 else f"1-{count}"


def genres(game):
    """GameTDB's lower-case genre list, presentably cased."""
    names = []
    for part in text_of(game, 'genre').split(','):
        part = part.strip().lower()
        if not part:
            continue
        name = GENRE_CASE.get(part, part.title())
        if name not in names:
            names.append(name)
    return ', '.join(names)


def media_links(system, game_id, region, languages, mirror):
    """Mirror links for one game, one per custom-database media field.

    Each field walks its art types in quality order and, within a type, the
    game's language priority; the first file present in the mirror wins.
    """
    links = {}
    langs = language_priority(region, languages)

    for field, art_types in MEDIA_FIELDS.items():
        for art_type, _ext in art_types:
            available = mirror.get((system, art_type))
            if not available:
                continue
            match = next((lang for lang in langs if (lang, game_id) in available), None)
            if match:
                links[field] = art_media_url(system, art_type, match, game_id)
                break
    return links


def index_mirror(system):
    """Scan the artwork mirror once: {(system, art_type): {(lang, id)}}.

    One directory walk up front is far cheaper than an existence check per
    game per art type per candidate language.
    """
    index = {}
    root = os.path.join(MEDIA_ROOT, system)
    if not os.path.isdir(root):
        return index

    for art_type in sorted(os.listdir(root)):
        type_dir = os.path.join(root, art_type)
        if not os.path.isdir(type_dir):
            continue
        present = set()
        for lang in os.listdir(type_dir):
            lang_dir = os.path.join(type_dir, lang)
            if not os.path.isdir(lang_dir):
                continue
            for filename in os.listdir(lang_dir):
                game_id, ext = os.path.splitext(filename)
                if ext:
                    present.add((lang, game_id))
        if present:
            index[(system, art_type)] = present
    return index


def convert(xml_path, output_dir):
    """Convert one GameTDB XML database and write the JSON it produces."""
    system = system_from_xml(xml_path)
    mirror = index_mirror(system)

    mirrored = sum(len(v) for v in mirror.values())
    if mirrored:
        types = ', '.join(sorted(art_type for _, art_type in mirror))
        print(f"  mirror: {mirrored} files ({types})")
    else:
        print(f"  mirror: empty -- run fetch_art.py to add artwork for '{system}'")

    section = SITE_SECTION.get(system, system.upper())
    games = {}
    skipped = 0

    for _event, element in ET.iterparse(xml_path, events=('end',)):
        if element.tag != 'game':
            continue

        game_id = text_of(element, 'id')
        available = locales(element)
        name = game_name(element, available)

        if not game_id or not name:
            skipped += 1
            element.clear()
            continue

        region = text_of(element, 'region')
        languages = text_of(element, 'languages')

        entry = {
            'id': game_id,
            'url': f"https://www.gametdb.com/{section}/{game_id}",
            'name': name,
        }

        for key, value in (
            ('developer', text_of(element, 'developer')),
            ('publisher', text_of(element, 'publisher')),
            ('genre', genres(element)),
            ('release_date', release_date(element)),
            ('nbplayers', players(element)),
            ('description', game_description(element, available)),
        ):
            if value:
                entry[key] = value

        entry.update(media_links(system, game_id, region, languages, mirror))

        # Later entries win: GameTDB lists the same id at most once, so this
        # only matters for malformed input.
        games[game_id] = entry
        element.clear()

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"gametdb_{system}.json")
    with open(output_path, 'w', encoding='utf-8') as handle:
        json.dump(games, handle, ensure_ascii=False, indent=2)

    with_media = sum(1 for g in games.values() if any(f in g for f in MEDIA_FIELDS))
    print(f"  {len(games)} games -> {output_path}")
    print(f"  {with_media} with artwork" + (f", {skipped} skipped (no id or title)" if skipped else ''))
    return games


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('xml', nargs='*',
                        help='GameTDB XML files (default: every *tdb.xml beside this script)')
    parser.add_argument('--output-dir', default=CUSTOM_DB_DIR,
                        help='where to write the JSON databases (default: var/db/custom)')
    args = parser.parse_args()

    paths = args.xml
    if not paths:
        paths = [os.path.join(SCRIPT_DIR, name)
                 for name in sorted(os.listdir(SCRIPT_DIR))
                 if name.endswith('tdb.xml')]

    if not paths:
        print(f"No *tdb.xml found in {SCRIPT_DIR}", file=sys.stderr)
        return 1

    for path in paths:
        if not os.path.exists(path):
            print(f"Not found: {path}", file=sys.stderr)
            return 1
        print(f"{os.path.basename(path)}:")
        convert(path, args.output_dir)

    return 0


if __name__ == '__main__':
    sys.exit(main())
