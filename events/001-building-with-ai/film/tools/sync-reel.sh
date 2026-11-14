#!/usr/bin/env bash
# Builds the 9:16 reel project (default: build/reel) from this one.
# The scenes are format-aware (window.BS_FMT); this copies them and flips the frame size.
# Edit the scenes here, never in the reel copy: the next sync overwrites it.
# Portable to GNU and BSD (macOS) tools: no rsync, and sed -i always takes a suffix.
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
DST="${1:-$SRC/build/reel}"
mkdir -p "$DST"
rm -rf "$DST/assets" "$DST/compositions"
cp -RL "$SRC/assets" "$DST/assets"
cp -R "$SRC/compositions" "$DST/compositions"
cp "$SRC/hyperframes.json" "$SRC/package.json" "$DST/"
[ -f "$DST/meta.json" ] || printf '{\n  "id": "builders-salon-reel",\n  "name": "builders-salon-reel"\n}\n' > "$DST/meta.json"
sed -i.bak 's/data-width="1920" data-height="1080"/data-width="1080" data-height="1920"/' "$DST"/compositions/*.html
rm -f "$DST"/compositions/*.bak
sed -e 's/window.BS_FMT = "wide"/window.BS_FMT = "reel"/' \
    -e 's/width=1920, height=1080/width=1080, height=1920/' \
    -e 's/width: 1920px;/width: 1080px;/' -e 's/height: 1080px;/height: 1920px;/' \
    -e 's/data-width="1920"/data-width="1080"/g' -e 's/data-height="1080"/data-height="1920"/g' \
    "$SRC/index.html" > "$DST/index.html"
grep -q 'BS_FMT = "reel"' "$DST/index.html"
echo "synced reel project -> $DST"
