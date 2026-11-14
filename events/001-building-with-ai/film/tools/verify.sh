#!/usr/bin/env bash
# Rebuilds the checked-in film inputs (data.js, field.js, score.wav) in a scratch copy and
# compares them byte for byte with the committed files. Exit 1 on any difference.
set -euo pipefail
FILM="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"
PY311="${FILM_PYTHON:-python3.11}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cp -r "$FILM/../artwork" "$TMP/artwork"
mkdir "$TMP/film"
for f in "$FILM"/*; do
  case "$(basename "$f")" in build|renders) ;; *) cp -R "$f" "$TMP/film/" ;; esac
done
cd "$TMP/film"
"$PY311" tools/prep.py >/dev/null
"$PY" tools/field.py >/dev/null
"$PY" tools/score.py build/score-raw.wav >/dev/null
ffmpeg -loglevel error -y -i build/score-raw.wav -af loudnorm=I=-14:TP=-1.0:LRA=11 -ar 48000 build/score.wav

status=0
check() {
  if cmp -s "$1" "$FILM/$2"; then echo "same      $2"; else echo "DIFFERENT $2"; status=1; fi
}
check assets/data.js assets/data.js
check assets/field.js assets/field.js
check build/score.wav assets/audio/score.wav
exit $status
