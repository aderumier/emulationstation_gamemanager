#!/usr/bin/env bash
# recreate_tree.sh
# Usage:
#   cat liste.txt | ./recreate_tree.sh [--dry-run] [--content "text"]

set -euo pipefail

DRY_RUN=0
CONTENT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift;;
    --content) CONTENT="$2"; shift 2;;
    -h|--help)
      echo "Usage: $0 [--dry-run] [--content TEXT] < paths.txt"
      exit 0;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

run() {
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "[DRY] $*"
  else
    eval "$@"
  fi
}

is_directory_guess() {
  local path="$1"
  # si finit par / → dir
  if [[ "$path" == */ ]]; then
    return 0
  fi
  # si pas d'extension → dir
  local base="${path##*/}"
  if [[ "$base" != *.* ]]; then
    return 0
  fi
  return 1
}

while IFS= read -r rawline || [[ -n "$rawline" ]]; do
  line="$(echo "$rawline" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  [[ -z "$line" || "${line:0:1}" == "#" ]] && continue

  if is_directory_guess "$line"; then
    line="${line%/}"
    if [[ $DRY_RUN -eq 1 ]]; then
      echo "[DRY] mkdir -p \"$line\""
    else
      mkdir -p -- "$line"
      echo "DIR  -> $line"
    fi
  else
    dir=$(dirname -- "$line")
    if [[ "$dir" != "." ]]; then
      if [[ $DRY_RUN -eq 1 ]]; then
        echo "[DRY] mkdir -p \"$dir\""
      else
        mkdir -p -- "$dir"
      fi
    fi
    if [[ -n "$CONTENT" ]]; then
      if [[ $DRY_RUN -eq 1 ]]; then
        echo "[DRY] file with content \"$line\""
      else
        printf "%s\n" "$CONTENT" > "$line"
        echo "FILE -> $line (with content)"
      fi
    else
      if [[ $DRY_RUN -eq 1 ]]; then
        echo "[DRY] touch \"$line\""
      else
        touch -- "$line"
        echo "FILE -> $line"
      fi
    fi
  fi
done
