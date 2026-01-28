#!/usr/bin/env bash
set -euo pipefail

# Extract files from a FAT32 filesystem inside a disk image (.img/.vhd/...) and zip them.
# Supports partitioned images (MBR/GPT) or raw FAT images.

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 <path/to/disk.(img|vhd|...)> [output.zip]"
  exit 1
fi

DISK="$(readlink -f "$1")"
if [[ ! -f "$DISK" ]]; then
  echo "Error: disk image not found: $DISK"
  exit 1
fi

OUTZIP="${2:-$(basename "${DISK%.*}").zip}"
OUTZIP="$(readlink -m "$OUTZIP")"

WORKDIR="$(mktemp -d)"
MNTDIR="$WORKDIR/mnt"
EXTRACTDIR="$WORKDIR/extracted"
mkdir -p "$MNTDIR" "$EXTRACTDIR"

MODE=""          # "loop" or "nbd"
LOOPDEV=""
NBDDEV=""

cleanup() {
  set +e
  if mountpoint -q "$MNTDIR"; then
    sudo umount "$MNTDIR"
  fi

  if [[ "$MODE" == "loop" && -n "${LOOPDEV:-}" ]]; then
    sudo losetup -d "$LOOPDEV" 2>/dev/null
  fi

  if [[ "$MODE" == "nbd" && -n "${NBDDEV:-}" ]]; then
    sudo qemu-nbd --disconnect "$NBDDEV" 2>/dev/null
  fi

  rm -rf "$WORKDIR"
}
trap cleanup EXIT

echo "Disk:   $DISK"
echo "Output: $OUTZIP"

# Decide how to attach:
# - If it's a plain .img, loop is fine.
# - For .vhd (and many other formats), use qemu-nbd.
ext="${DISK##*.}"
ext="${ext,,}"

if [[ "$ext" == "img" ]]; then
  MODE="loop"
  LOOPDEV="$(sudo losetup --find --show --partscan "$DISK")"
  DEVBASE="$LOOPDEV"
  echo "Attached via loop: $DEVBASE"
else
  MODE="nbd"
  # Ensure nbd module is available
  sudo modprobe nbd max_part=16

  # Find a free /dev/nbdX
  for d in /dev/nbd{0..15}; do
    if ! lsblk -no MOUNTPOINT "$d" 2>/dev/null | grep -q . && ! sudo lsof "$d" >/dev/null 2>&1; then
      NBDDEV="$d"
      break
    fi
  done

  if [[ -z "$NBDDEV" ]]; then
    echo "Error: no free /dev/nbd device found (tried /dev/nbd0..15)"
    exit 1
  fi

  sudo qemu-nbd --connect="$NBDDEV" "$DISK"

  # Give the kernel a moment and force partition re-read
  sudo partprobe "$NBDDEV" 2>/dev/null || true
  udevadm settle 2>/dev/null || true

  DEVBASE="$NBDDEV"
  echo "Attached via nbd:  $DEVBASE"
fi

# Find a vfat (FAT32) partition; otherwise try mounting the whole device.
FAT_DEV=""

# First try partitions (e.g., /dev/loop0p1 or /dev/nbd0p1)
for p in "${DEVBASE}"p*; do
  [[ -b "$p" ]] || continue
  t="$(sudo blkid -o value -s TYPE "$p" 2>/dev/null || true)"
  if [[ "${t,,}" == "vfat" ]]; then
    FAT_DEV="$p"
    break
  fi
done

# If no vfat partition found, maybe the whole image is a raw FAT filesystem
if [[ -z "$FAT_DEV" ]]; then
  t="$(sudo blkid -o value -s TYPE "$DEVBASE" 2>/dev/null || true)"
  if [[ "${t,,}" == "vfat" ]]; then
    FAT_DEV="$DEVBASE"
  fi
fi

if [[ -z "$FAT_DEV" ]]; then
  echo "Error: could not find a FAT(vfat) filesystem in: $DISK"
  echo "Tip: run: sudo blkid ${DEVBASE}*  to inspect partitions/filesystems."
  exit 1
fi

echo "Mounting (read-only): $FAT_DEV"
sudo mount -o ro "$FAT_DEV" "$MNTDIR"

echo "Copying files out..."
rsync -a "$MNTDIR"/ "$EXTRACTDIR"/

echo "Creating zip..."
(
  cd "$EXTRACTDIR"
  zip -r -9 "$OUTZIP" .
)

echo "Done: $OUTZIP"
