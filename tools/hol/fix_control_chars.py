#!/usr/bin/env python3
"""
Fix NULL bytes and control characters in HOL/amigahol JSON database.
Use after scraping or to repair an existing var/db/custom/amigahol.json
so it can be used with gamelist XML (lxml rejects control chars).

Usage:
  python fix_control_chars.py [path_to_json]
  Default path: ../../var/db/custom/amigahol.json (from tools/hol/)
"""

import json
import os
import sys


def _sanitize_text(s: str) -> str:
    """Remove NULL bytes and control characters (JSON/XML safe)."""
    if s is None or not isinstance(s, str):
        return s if s is not None else ''
    result = []
    for c in s:
        code = ord(c)
        if code == 0x9 or code == 0xA or code == 0xD:
            result.append(c)
        elif 0x20 <= code <= 0xD7FF or 0xE000 <= code <= 0xFFFD or (0x10000 <= code <= 0x10FFFF):
            result.append(c)
    return ''.join(result)


def _sanitize_dict_strings(obj):
    """Recursively sanitize all string values in a dict/list (in place)."""
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            obj[k] = _sanitize_dict_strings(v)
        return obj
    if isinstance(obj, list):
        for i, v in enumerate(obj):
            obj[i] = _sanitize_dict_strings(v)
        return obj
    if isinstance(obj, str):
        return _sanitize_text(obj)
    return obj


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_path = os.path.join(script_dir, '..', '..', 'var', 'db', 'custom', 'amigahol.json')
    path = sys.argv[1] if len(sys.argv) > 1 else default_path
    path = os.path.normpath(path)

    if not os.path.exists(path):
        print(f"File not found: {path}")
        sys.exit(1)

    print(f"Loading: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, dict):
        print("Expected a JSON object (dict) at root.")
        sys.exit(1)

    _sanitize_dict_strings(data)
    print(f"Writing back: {path}")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("Done. All string values are now free of NULL/control characters.")


if __name__ == '__main__':
    main()
