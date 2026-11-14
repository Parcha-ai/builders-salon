#!/usr/bin/env bash
# Builds the 9:16 reel project (default: build/reel) from this one.
# The scenes are format-aware (window.BS_FMT); this copies them and flips the frame size.
# Edit the scenes here, never in the reel copy: the next sync overwrites it.
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
DST="${1:-$SRC/build/reel}"
mkdir -p "$DST"
rsync -aL --delete "$SRC/assets/" "$DST/assets/"
rsync -a --delete "$SRC/compositions/" "$DST/compositions/"
cp "$SRC/hyperframes.json" "$SRC/package.json" "$DST/"
[ -f "$DST/meta.json" ] || printf '{\n  "id": "builders-salon-reel",\n  "name": "builders-salon-reel"\n}\n' > "$DST/meta.json"
sed -i 's/data-width="1920" data-height="1080"/data-width="1080" data-height="1920"/' "$DST"/compositions/*.html
sed -e 's/window.BS_FMT = "wide"/window.BS_FMT = "reel"/' \
    -e 's/width=1920, height=1080/width=1080, height=1920/' \
    -e 's/width: 1920px;/width: 1080px;/' -e 's/height: 1080px;/height: 1920px;/' \
    -e 's/data-width="1920"/data-width="1080"/g' -e 's/data-height="1080"/data-height="1920"/g' \
    "$SRC/index.html" > "$DST/index.html"
grep -q 'BS_FMT = "reel"' "$DST/index.html"
echo "synced reel project -> $DST"
