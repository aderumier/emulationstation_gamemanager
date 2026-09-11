#!/usr/bin/env python3
"""
Fill the local GameTDB artwork mirror under var/db/custom/medias/gametdb/.

GameTDB serves artwork two ways, and this tool uses both:

  zips    GameTDB publishes zip archives of the medium covers, cartridges and
          labels, one per system per language. Downloading a few dozen
          archives is enormously cheaper than fetching tens of thousands of
          files one at a time, so this runs first and does most of the work.

  covers  The high-quality covers (coverHQ, 1166x1888, and coverfullHQ, the
          full wrap) have no archive and must be fetched file by file.
          art.gametdb.com answers only a few requests a second, so this pass
          is slow by nature and works hard to stay small: it asks only in the
          languages the zip pass proved a cover exists in, takes them in the
          order the converter prefers and stops at the first hit, skips the
          packaging art of download-only releases, and records its misses so
          re-runs skip everything already settled.

Usage:
  python fetch_art.py switch              # zips, then high-quality covers
  python fetch_art.py switch 3ds          # several systems
  python fetch_art.py switch --zips-only  # just the archives (minutes)
  python fetch_art.py switch --covers-only
  python fetch_art.py switch --langs US,EN,JA

Archives can also be downloaded by hand -- gametdb.com is slow, and sometimes
refuses a host outright -- by saving them into tools/gametdb/zips/ under the
names GameTDB gives them. They are picked up automatically; add --offline to
unpack only those and skip the site entirely.
"""

import argparse
import io
import json
import os
import re
import sys
import time
import zipfile
from xml.etree import ElementTree as ET

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gametdb import (
    ART_TYPES,
    MEDIA_FIELDS,
    MEDIA_ROOT,
    SITE_SECTION,
    ZIP_TYPES,
    art_path,
    art_url,
    language_priority,
    system_from_xml,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DOWNLOADS_URL = 'https://www.gametdb.com/{section}/Downloads'
ZIP_URL = 'https://www.gametdb.com/download.php?FTP={name}'

USER_AGENT = 'Mozilla/5.0 (cursorscraper gametdb art mirror)'

# www.gametdb.com is slow to render its pages; the art CDN is quick but
# rate-limited, so the two get very different timeouts.
SITE_TIMEOUT = 180
ART_TIMEOUT = 30

# art.gametdb.com serves roughly three requests a second and stops answering
# altogether for a while if pushed harder, so the cover pass paces itself by
# default rather than finding that limit again.
DEFAULT_DELAY = 0.35

# Consecutive connection failures before giving up: once the host has stopped
# answering, continuing only prolongs whatever cooling-off period is in force.
MAX_CONSECUTIVE_ERRORS = 12

# Languages tried per media field before accepting that the game has no art of
# that kind. Covers almost always sit in one of a game's first few languages,
# and without a bound a worldwide release with covers in a dozen languages
# would cost a dozen requests to prove a missing full wrap.
DEFAULT_MAX_TRIES = 3

# Misses of one art type, with no hit at all, before concluding GameTDB simply
# does not carry that type for the system and dropping it for the rest of the run.
ABANDON_AFTER = 400

# Archives named ..._weekNN contain only that week's additions, which the full
# archive already includes.
WEEKLY_ZIP = re.compile(r'_week\d+$')

# Where archives downloaded by hand are picked up, and the names they must keep:
# GameTDB-switch_coverM-US-2026-09-09.zip, the date optional.
ZIP_DIR = os.path.join(SCRIPT_DIR, 'zips')
ZIP_NAME = re.compile(
    r'^GameTDB-(?P<system>[A-Za-z0-9]+)_(?P<type>[A-Za-z0-9_]+)'
    r'-(?P<lang>[A-Za-z]{2})(?:-(?P<date>[\d-]+))?\.zip$', re.IGNORECASE)

# Ids that returned 404, so a re-run does not ask again. Kept next to the
# artwork it describes.
MISSES_FILE = 'misses.json'


def session():
    handle = requests.Session()
    handle.headers['User-Agent'] = USER_AGENT
    return handle


def load_misses(system):
    """Previously recorded 404s: {art_type: {lang: [ids]}}."""
    path = os.path.join(MEDIA_ROOT, system, MISSES_FILE)
    try:
        with open(path, encoding='utf-8') as handle:
            raw = json.load(handle)
    except (OSError, ValueError):
        return {}
    return {art_type: {lang: set(ids) for lang, ids in langs.items()}
            for art_type, langs in raw.items()}


def save_misses(system, misses):
    path = os.path.join(MEDIA_ROOT, system, MISSES_FILE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    serialisable = {art_type: {lang: sorted(ids) for lang, ids in langs.items()}
                    for art_type, langs in misses.items()}
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(serialisable, handle, indent=1)


# ---------------------------------------------------------------------------
# Archive pass
# ---------------------------------------------------------------------------

def list_zips(handle, system):
    """Current archive names on GameTDB's download page, newest date only.

    Names carry a build date -- GameTDB-switch_coverM-US-2026-09-09.zip -- so
    they are discovered rather than constructed.
    """
    section = SITE_SECTION.get(system, system.upper())
    response = handle.get(DOWNLOADS_URL.format(section=section), timeout=SITE_TIMEOUT)
    response.raise_for_status()

    found = {}
    pattern = re.compile(
        r'FTP=(GameTDB-' + re.escape(system) + r'_([A-Za-z0-9_]+)-([A-Z]{2})-[\d-]+\.zip)')
    for name, art_type, lang in pattern.findall(response.text):
        if WEEKLY_ZIP.search(art_type) or art_type not in ART_TYPES:
            continue
        found[(art_type, lang)] = name
    return found


def extract_zip(data, system, art_type, lang):
    """Unpack one archive into the mirror, returning how many files are new.

    Archive layouts vary, so files are placed by their basename rather than by
    whatever directory the archive happens to use.
    """
    ext = ART_TYPES[art_type]
    target_dir = os.path.join(MEDIA_ROOT, system, art_type, lang)
    os.makedirs(target_dir, exist_ok=True)

    added = 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            name = os.path.basename(member.filename)
            game_id, member_ext = os.path.splitext(name)
            if not game_id or member_ext.lower() != ext:
                continue
            target = os.path.join(target_dir, game_id + ext)
            if os.path.exists(target):
                continue
            with archive.open(member) as source, open(target, 'wb') as out:
                out.write(source.read())
            added += 1
    return added


def local_zips(zip_dir, system):
    """Archives already downloaded by hand: {(art_type, lang): path}.

    gametdb.com is slow and sometimes refuses this host altogether, so its
    archives can simply be saved from a browser into the drop folder. Keep the
    names GameTDB gives them -- that is where the system, art type and language
    come from. Where two builds of the same archive are present the newer one
    wins.
    """
    found, dates = {}, {}
    if not os.path.isdir(zip_dir):
        return found

    for name in sorted(os.listdir(zip_dir)):
        match = ZIP_NAME.match(name)
        if not match or match.group('system').lower() != system.lower():
            continue
        art_type, lang = match.group('type'), match.group('lang').upper()
        if WEEKLY_ZIP.search(art_type) or art_type not in ART_TYPES:
            continue
        date = match.group('date') or ''
        key = (art_type, lang)
        if key not in found or date >= dates[key]:
            found[key], dates[key] = os.path.join(zip_dir, name), date
    return found


def sync_zips(handle, system, wanted_types, wanted_langs, zip_dir, offline):
    """Unpack the archives for a system, from the drop folder and the site."""
    def wanted(key):
        return key[0] in wanted_types and (not wanted_langs or key[1] in wanted_langs)

    total = 0
    done = set()

    # Hand-downloaded archives first: they cost nothing and mean the site does
    # not have to be asked for them.
    on_disk = {key: path for key, path in local_zips(zip_dir, system).items() if wanted(key)}
    if on_disk:
        print(f"[{system}] {len(on_disk)} archives in {zip_dir}")
        for (art_type, lang), path in sorted(on_disk.items()):
            try:
                with open(path, 'rb') as handle_in:
                    added = extract_zip(handle_in.read(), system, art_type, lang)
            except (OSError, zipfile.BadZipFile) as error:
                print(f"  {os.path.basename(path)}: unreadable ({error})", file=sys.stderr)
                continue
            done.add((art_type, lang))
            total += added
            print(f"  {art_type}/{lang}: {added} new")

    if offline:
        print(f"[{system}] archives done, {total} new files (offline)")
        return

    print(f"[{system}] looking up further archives on gametdb.com ...")
    try:
        available = list_zips(handle, system)
    except requests.RequestException as error:
        print(f"[{system}] could not read the download page: {error}\n"
              f"  Download the archives by hand into {zip_dir} and re-run with --offline.",
              file=sys.stderr)
        print(f"[{system}] archives done, {total} new files")
        return

    selected = sorted(key for key in available if wanted(key) and key not in done)
    if not selected:
        print(f"[{system}] nothing further published for the requested types")
        print(f"[{system}] archives done, {total} new files")
        return

    print(f"[{system}] {len(selected)} archives to fetch")
    for art_type, lang in selected:
        name = available[(art_type, lang)]
        try:
            response = handle.get(ZIP_URL.format(name=name), timeout=SITE_TIMEOUT)
            response.raise_for_status()
            added = extract_zip(response.content, system, art_type, lang)
        except (requests.RequestException, zipfile.BadZipFile) as error:
            print(f"  {art_type}/{lang}: failed ({error})", file=sys.stderr)
            continue
        total += added
        print(f"  {art_type}/{lang}: {added} new")
    print(f"[{system}] archives done, {total} new files")


# ---------------------------------------------------------------------------
# High-quality cover pass
# ---------------------------------------------------------------------------

def read_games(system):
    """(id, region, languages, physical) for every game in the system's XML."""
    path = next((os.path.join(SCRIPT_DIR, name)
                 for name in sorted(os.listdir(SCRIPT_DIR))
                 if name.endswith('.xml') and system_from_xml(name) == system), None)
    if not path:
        return []

    games = []
    for _event, element in ET.iterparse(path, events=('end',)):
        if element.tag != 'game':
            continue
        game_id = (element.findtext('id') or '').strip()
        if game_id:
            games.append((game_id,
                          (element.findtext('region') or '').strip(),
                          (element.findtext('languages') or '').strip(),
                          is_physical(element.findtext('type') or '')))
        element.clear()
    return games


def is_physical(game_type):
    """Whether a release came on a card, and so can have a cartridge scan.

    Three quarters of the Switch database is eShop-only, and asking the CDN for
    cartridge art those titles never had would dominate the whole pass.
    """
    name = game_type.strip().lower()
    return not (name in ('eshop', 'homebrew', 'dsiware', 'wiiware', 'custom')
                or name.startswith('vc-')
                or name.endswith('ware'))


def mirrored_langs(system, art_type):
    """{game id: {languages mirrored}} for one art type."""
    index = {}
    root = os.path.join(MEDIA_ROOT, system, art_type)
    if not os.path.isdir(root):
        return index
    for lang in os.listdir(root):
        lang_dir = os.path.join(root, lang)
        if not os.path.isdir(lang_dir):
            continue
        for filename in os.listdir(lang_dir):
            game_id, ext = os.path.splitext(filename)
            if ext:
                index.setdefault(game_id, set()).add(lang)
    return index


def cover_targets(system, wanted_langs, max_tries, misses):
    """What is worth fetching, as (game id, field, [(art_type, lang), ...]).

    The attempts for a field follow exactly the order convert.py prefers, so
    the first one that succeeds is the file the database will use and the rest
    of that field can be abandoned.

    Three things keep the pass small. Languages are restricted to the ones the
    archive pass proved a cover exists in -- a game with no cover at all in
    some language almost never has a high-quality one, and guessing blindly
    would multiply the work by the whole language list. Scanning a field stops
    at the first art type already in the mirror, since nothing below it can
    ever be chosen: there is no point fetching a 160x260 cover when the
    352x570 one from the archives is already on disk. And the two fields that
    describe physical packaging are skipped for download-only releases, which
    are three quarters of the Switch database.
    """
    have_medium = mirrored_langs(system, 'coverM')

    for game_id, region, languages, physical in read_games(system):
        known = have_medium.get(game_id)
        if not known:
            continue
        langs = [lang for lang in language_priority(region, languages)
                 if lang in known and (not wanted_langs or lang in wanted_langs)]
        langs = langs[:max_tries]
        if not langs:
            continue

        for field, art_types in MEDIA_FIELDS.items():
            if field in ('boxback', 'cartridge') and not physical:
                continue

            attempts = []
            for art_type, _ext in art_types:
                if any(os.path.exists(art_path(system, art_type, lang, game_id))
                       for lang in langs):
                    # The converter would stop here, so nothing below is worth
                    # asking for. What is queued above it still is: those types
                    # are better, and it would prefer them.
                    break
                if art_type not in ZIP_TYPES:
                    seen = misses.get(art_type, {})
                    attempts.extend((art_type, lang) for lang in langs
                                    if game_id not in seen.get(lang, ()))

            if attempts:
                yield game_id, field, attempts


def fetch_covers(handle, system, wanted_langs, delay, max_tries):
    """Fetch high-quality covers one file at a time, resuming where left off."""
    misses = load_misses(system)
    targets = list(cover_targets(system, wanted_langs, max_tries, misses))

    if not targets:
        print(f"[{system}] nothing left to fetch -- if the mirror is empty, run the "
              f"archive pass first so the language of each game's cover is known")
        return

    requests_due = sum(len(attempts) for _gid, _field, attempts in targets)
    print(f"[{system}] {len(targets)} fields to resolve, at most {requests_due} requests "
          f"(art.gametdb.com answers a few per second, so this takes a while)")

    downloaded = notfound = 0
    errors = 0
    started = time.time()
    blocked = False

    # Not every art type exists for every system -- GameTDB has no coverfull
    # for the Switch at all, for instance. Rather than hard-coding which,
    # abandon a type that has answered nothing but 404 for a long run of games.
    hits = {}
    tried = {}
    abandoned = set()

    try:
        for done, (game_id, _field, attempts) in enumerate(targets, 1):
            for art_type, lang in attempts:
                if art_type in abandoned:
                    continue

                seen = misses.setdefault(art_type, {})
                target = art_path(system, art_type, lang, game_id)
                try:
                    response = handle.get(art_url(system, art_type, lang, game_id),
                                          timeout=ART_TIMEOUT)
                except requests.RequestException as error:
                    # A failed request is not evidence the file is missing, so
                    # it is left unrecorded and retried on the next run.
                    errors += 1
                    print(f"  {art_type}/{lang}/{game_id}: {error}", file=sys.stderr)
                    if errors >= MAX_CONSECUTIVE_ERRORS:
                        blocked = True
                    break

                errors = 0
                tried[art_type] = tried.get(art_type, 0) + 1
                if delay:
                    time.sleep(delay)

                if response.status_code == 200 and response.content:
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with open(target, 'wb') as out:
                        out.write(response.content)
                    hits[art_type] = hits.get(art_type, 0) + 1
                    downloaded += 1
                    break

                if response.status_code == 404:
                    seen.setdefault(lang, set()).add(game_id)
                    notfound += 1
                    if not hits.get(art_type) and tried[art_type] >= ABANDON_AFTER:
                        abandoned.add(art_type)
                        print(f"  no '{art_type}' anywhere in {tried[art_type]} tries; "
                              f"GameTDB does not seem to have it for {system} -- skipping "
                              f"the rest", file=sys.stderr)
                    continue

                if response.status_code == 429:
                    print("  rate limited -- pausing for a minute", file=sys.stderr)
                    time.sleep(60)
                    break

                # Anything else -- a server error, or a 200 with an empty body --
                # says nothing about whether the file exists, so it is left out
                # of the miss cache and tried again on the next run.
                print(f"  {art_type}/{lang}/{game_id}: unexpected HTTP "
                      f"{response.status_code}, {len(response.content)} bytes",
                      file=sys.stderr)
                break

            if blocked:
                print("\n  art.gametdb.com stopped answering; it rejects sustained "
                      "traffic for a while once pushed.\n"
                      "  Progress is saved -- wait a while, then re-run, ideally with "
                      "a larger --delay.", file=sys.stderr)
                break

            if done % 200 == 0:
                rate = done / max(time.time() - started, 1e-9)
                left = (len(targets) - done) / rate
                print(f"  {done}/{len(targets)}  {downloaded} saved, {notfound} absent "
                      f"(~{left / 60:.0f} min left)")
                save_misses(system, misses)
    except KeyboardInterrupt:
        print("\n  interrupted -- progress is saved, re-run to continue")
    finally:
        save_misses(system, misses)

    print(f"[{system}] covers done: {downloaded} saved, {notfound} absent")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('systems', nargs='+', help="e.g. switch 3ds")
    parser.add_argument('--zips-only', action='store_true',
                        help='only download the archives')
    parser.add_argument('--covers-only', action='store_true',
                        help='only fetch the high-quality covers')
    parser.add_argument('--langs',
                        help='restrict to these art languages, e.g. US,EN,JA')
    parser.add_argument('--types', default=','.join(ZIP_TYPES),
                        help=f'archive types to mirror (default: {",".join(ZIP_TYPES)})')
    parser.add_argument('--zip-dir', default=ZIP_DIR,
                        help=f'folder holding archives downloaded by hand '
                             f'(default: {os.path.relpath(ZIP_DIR)})')
    parser.add_argument('--offline', action='store_true',
                        help='unpack only the archives already in --zip-dir, '
                             'never contacting gametdb.com')
    parser.add_argument('--delay', type=float, default=DEFAULT_DELAY,
                        help=f'seconds to pause between cover requests '
                             f'(default: {DEFAULT_DELAY})')
    parser.add_argument('--max-tries', type=int, default=DEFAULT_MAX_TRIES,
                        help=f'languages to try per media field before giving up '
                             f'(default: {DEFAULT_MAX_TRIES})')
    args = parser.parse_args()

    wanted_langs = {lang.strip().upper()
                    for lang in (args.langs or '').split(',') if lang.strip()}
    wanted_types = {name.strip() for name in args.types.split(',') if name.strip()}

    unknown = wanted_types - set(ART_TYPES)
    if unknown:
        print(f"Unknown art types: {', '.join(sorted(unknown))}", file=sys.stderr)
        return 1

    handle = session()
    for system in args.systems:
        if not args.covers_only:
            sync_zips(handle, system, wanted_types, wanted_langs,
                      args.zip_dir, args.offline)
        if not args.zips_only:
            fetch_covers(handle, system, wanted_langs, args.delay, args.max_tries)

    return 0


if __name__ == '__main__':
    sys.exit(main())
