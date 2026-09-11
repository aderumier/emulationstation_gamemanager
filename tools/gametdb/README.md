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
during a scrape is not an option either: **art.gametdb.com refuses this address
outright for the best part of an hour if it is hit concurrently**, so a scraper
that fetched from it per game would be a liability.

So the artwork is fetched once into a local mirror, and the JSON database points
at that mirror. Every link in the database is then a file that demonstrably
exists, and scraping a whole system is a local file copy.

### What the host actually tolerates

Measured, rather than assumed: the CDN is **HTTP/1.1 only** (it offers no h2 over
ALPN), and a single `requests.Session` holds one keep-alive connection for the
whole run — 30 requests opened exactly one socket. On that one connection it
serves 10–45 requests a second quite happily.

Concurrency is the thing it objects to, not volume. Three connections measure
about twice as fast as one; six measure *slower* than three; and a 64-thread
burst is what got this address blocked in the first place. So `fetch_art.py`
stays strictly sequential — only ever one request in flight — and adds a
jittered delay on top to sit well under the rate the server would allow. That
turns a thirty-minute job into an hour or two, which is the right trade for not
being locked out again.

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
file at a time, at the deliberately restrained pace described above. Six things
keep the pass as small as it can be:

- it asks only in the languages the archive pass proved a cover exists in,
  rather than guessing across the whole language list;
- it takes those in the same priority order the converter uses and stops at the
  first hit, so a game that has its cover costs one request;
- it caps that at `--max-tries` languages per field (3 by default), bounding
  what it costs to prove a game has *no* art of some kind;
- `--fields` limits which media fields it chases at all, and defaults to
  `boxfront`: the archives already supply the cartridge art, and the full wrap
  would roughly double the run for a field few collections display;
- it skips `boxback` and `cartridge` for download-only releases, which have
  neither a box nor a card — three quarters of the Switch database;
- it drops an art type entirely once several hundred requests have produced no
  hit at all, which is how it discovers that a system has no `coverfull`.

Misses are recorded in `<mirror>/<system>/misses.json`, so a re-run neither
re-downloads what is there nor re-asks for what is not. Interrupting it with
Ctrl-C is safe.

The run prints its own estimate on startup from the pace you chose. For Switch
that is around 17,400 covers at roughly 2 requests a second, so a couple of
hours; `--delay 0` would finish in about half an hour but gives up the safety
margin. If the CDN cuts you off the tool says so and stops; wait a while, then
re-run with a larger `--delay`.

Useful flags:

    python fetch_art.py switch --zips-only        # archives only, minutes
    python fetch_art.py switch --langs US,EN,JA   # restrict to some languages
    python fetch_art.py switch --delay 1.0        # go easier on the CDN
    python fetch_art.py switch --max-tries 1      # fastest, fewest covers found

## What ends up in the JSON

Keyed by release type and GameTDB id, so an entry says at a glance whether a
game came on a card or as a download:

```json
"Switch/A224A": {
  "id": "Switch/A224A",
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

The type prefix comes from the XML's `<type>`: `Switch` or `eShop` (4,811 and
17,267 of them), and on the 3DS `3DS`, `3DSWare`, `New3DS`, `VC-NES`, `VC-GB`
and the rest. `url` and the artwork paths keep the bare id, which is what
GameTDB addresses them by. A `customid` therefore reads
`gametdb_switch/Switch/A224A`; `parse_customid` splits on the first slash only,
so the type travels with the id as it should.

`name` comes from the game's English locale rather than the `<game name>`
attribute, which carries a language suffix — "Celeste (EN,FR,DE)" — that would
only get in the way of name matching.

### Localized names

`alt_names` carries the game's titles in the other languages GameTDB knows, and
the custom scrapper indexes them alongside the primary name, so a localized ROM
matches without being renamed:

    Pokémon Ultra Soleil          -> A2AP  Pokémon Ultra Sun
    PJ MASKS: HELDEN DER NACHT    -> A22EA PJ MASKS: HEROES OF THE NIGHT
    Horse Tales : La Vallée d'Emeraude -> A22VA Horse Tales: Emerald Valley Ranch

Only titles that survive matching intact are kept — 945 for Switch, 1,678 for
the 3DS, mostly French, Spanish, German, Italian and Portuguese. Matching
reduces a name to ASCII letters and digits, so a Japanese or Korean title comes
out as whatever Latin text it happened to contain: 짱구는 못말려…7일간의 여행
becomes a bare `7`, which would match almost any ROM. Titles that lose more than
half their characters that way are dropped.

Adding artwork or names means the index must be rebuilt. It now notices by
itself — it fingerprints the JSON files and rebuilds when they change — but
Settings → Cache → *Refresh Custom Scraper cache* forces it.

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
