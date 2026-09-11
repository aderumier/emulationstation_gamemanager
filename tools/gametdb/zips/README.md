# Drop folder for GameTDB art archives

Put GameTDB's artwork archives here and `fetch_art.py` unpacks them into the
mirror instead of downloading them. Useful because gametdb.com is slow, and
refuses some hosts outright for a while after heavy use — a browser generally
gets through when the tool cannot.

Get them from the Downloads page of the system you want:

- https://www.gametdb.com/Switch/Downloads
- https://www.gametdb.com/3DS/Downloads

Take the **coverM**, **cart** and **label** archives in the languages you care
about (`US` and `EN` cover most of a Western collection; add `JA` for imports).
Skip anything named `..._weekNN` — those are weekly deltas the full archives
already contain.

**Keep the filenames GameTDB gives them.** The system, art type and language are
read from the name:

    GameTDB-switch_coverM-US-2026-09-09.zip
            ^system ^type  ^lang ^build date (optional)

Then:

    python ../fetch_art.py switch --offline      # unpack these, touch nothing online
    python ../fetch_art.py switch                # unpack these, then fetch the rest

Where the same archive is here twice, the newer build wins. The archives
themselves are not committed — `*.zip` is in `.gitignore` — and can be deleted
once unpacked.

Note that GameTDB publishes **no archive for the high-quality covers**
(`coverHQ`, `coverfullHQ`); those only come from `fetch_art.py`'s second pass
against art.gametdb.com. With archives alone, `boxfront` falls back to the
352x570 `coverM`, which is still a perfectly usable database.
