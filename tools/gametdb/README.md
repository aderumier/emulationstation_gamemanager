# GameTDB

Turns GameTDB's XML databases into the custom JSON databases the scrapper reads
from `var/db/custom/`, with the artwork mirrored locally alongside them.

| file | what it does |
| --- | --- |
| `*tdb.xml` | the GameTDB databases, downloaded from gametdb.com |
| `fetch_art.py` | fills the artwork mirror under `var/db/custom/medias/gametdb/` |
| `convert.py` | writes `var/db/custom/gametdb_<system>.json` |
| `gametdb.py` | shared tables: systems, languages, art types, priority rules |
| `zips/` | drop folder for art archives downloaded by hand |

## Why the artwork is mirrored instead of linked

GameTDB's media URLs are built from the game id, so they cannot be trusted
sight-unseen — a Switch eShop title generally has no cartridge scan, and most
games have covers in only one or two languages. Checking them over the network
is not an option either: **art.gametdb.com answers roughly three requests per
second and stops answering at all for a while if pushed harder.** Scraping
directly from it would be painfully slow even once it worked.

So the artwork is fetched once into a local mirror, and the JSON database points
at that mirror. Every link in the database is then a file that demonstrably
exists, and scraping a whole system is a local file copy.

## Usage

    # 1. Mirror the artwork (see the timings below)
    python fetch_art.py switch 3ds

    # 2. Build the JSON databases
    python convert.py

Then pick `gametdb_switch` as the custom database for the system in the
scrapper's settings.

`convert.py` on its own produces text fields only, which is fine if artwork is
not wanted; re-run it after any `fetch_art.py` run to pick up new artwork.

## The two artwork passes

`fetch_art.py` runs two passes, and either can be run alone with `--zips-only`
or `--covers-only`.

**Archives** (minutes). GameTDB publishes zip archives of the medium covers
(`coverM`, 352x570), the cartridge scans (`cart`) and the cart labels (`label`),
one per system per language. A few dozen downloads cover a whole system.

These can also be downloaded by hand and dropped into [`zips/`](zips/) — worth
doing, since gametdb.com is slow and refuses some hosts outright for a while
after heavy use, while a browser usually gets through. Keep the filenames
GameTDB gives them; see [zips/README.md](zips/README.md). They are picked up
automatically, and `--offline` unpacks only those without contacting the site at
all:

    python fetch_art.py switch --offline --zips-only

**High-quality covers** (hours). `coverHQ` (1166x1888) and `coverfullHQ` (the
full back-spine-front wrap, 2454x1888) have no archive and must be fetched one
file at a time, against that three-per-second ceiling. Five things keep the
pass as small as it can be:

- it asks only in the languages the archive pass proved a cover exists in,
  rather than guessing across the whole language list;
- it takes those in the same priority order the converter uses and stops at the
  first hit, so a game that has its cover costs one request;
- it caps that at `--max-tries` languages per field (3 by default), bounding
  what it costs to prove a game has *no* art of some kind;
- it skips `boxback` and `cartridge` for download-only releases, which have
  neither a box nor a card — three quarters of the Switch database;
- it drops an art type entirely once several hundred requests have produced no
  hit at all, which is how it discovers that a system has no `coverfull`.

Misses are recorded in `<mirror>/<system>/misses.json`, so a re-run neither
re-downloads what is there nor re-asks for what is not. Interrupting it with
Ctrl-C is safe.

Expect a few hours for Switch's 22,000 games and under an hour for the 3DS. If
the CDN cuts you off the tool says so and stops; wait a while, then re-run,
optionally with a larger `--delay`.

Useful flags:

    python fetch_art.py switch --zips-only        # archives only, minutes
    python fetch_art.py switch --langs US,EN,JA   # restrict to some languages
    python fetch_art.py switch --delay 1.0        # go easier on the CDN
    python fetch_art.py switch --max-tries 1      # fastest, fewest covers found

## What ends up in the JSON

Keyed by GameTDB id:

```json
"A224A": {
  "id": "A224A",
  "url": "https://www.gametdb.com/Switch/A224A",
  "name": "Ni no Kuni II - Revenant Kingdom Prince's Edition",
  "developer": "...",
  "publisher": "BANDAI NAMCO Entertainment",
  "genre": "Action, Role-Playing",
  "release_date": "2017-09-17",
  "nbplayers": "1",
  "description": "...",
  "boxfront": "/var/db/custom/medias/gametdb/switch/coverHQ/US/A224A.jpg",
  "boxback": "/var/db/custom/medias/gametdb/switch/coverfullHQ/US/A224A.jpg",
  "cartridge": "/var/db/custom/medias/gametdb/switch/cart/US/A224A.png"
}
```

A media value is both the URL the browser loads and the file's path in the
repository, so the media picker displays it and the scrapper copies it without a
network request. Fields are omitted rather than written empty, and media fields
appear only when the file is in the mirror.

`name` comes from the game's English locale rather than the `<game name>`
attribute, which carries a language suffix — "Celeste (EN,FR,DE)" — that would
only get in the way of name matching.

### Media fields

| field | art types tried, best first |
| --- | --- |
| `boxfront` | `coverHQ`, `coverM`, `cover` |
| `boxback` | `coverfullHQ`, `coverfull` |
| `cartridge` | `cart`, `label` |

`boxback` gets the full wrap, since GameTDB has no separate back cover. Map
these onto gamelist fields under Settings → Scrappers → Custom; the defaults
(`boxfront`→`boxart`, `boxback`→`boxback`, `cartridge`→`cartridge`) already fit.

### Language priority

Artwork is keyed by language as well as by id, so each game gets the first
language that has a file: **US**, then **EN**, then the languages implied by the
game's `<region>`, then the ones it ships with, then everything else — a
Japanese cover beats no cover.

## Adding a system

The tools derive everything from the XML filename: drop `wiitdb.xml` in this
directory and `wii` works throughout. Only the game's page URL needs a hand —
add the system to `SITE_SECTION` in `gametdb.py` if GameTDB spells its section
differently from the file.

## Notes

- The mirror is not committed: `medias/` is in `.gitignore`, and the artwork for
  Switch alone runs to tens of thousands of files.
- GameTDB lists a handful of empty placeholder entries with an id but no title
  at all (11 of them for Switch); those are skipped.
- Re-download the `*tdb.xml` files from gametdb.com to refresh the text data,
  then re-run `convert.py`.
