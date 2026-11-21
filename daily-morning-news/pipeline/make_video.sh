#!/usr/bin/env bash
# Portable approved static-background pipeline; no system environment changes.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DIR="${1:?Usage: make_video.sh <report_dir>}"
MODELS="${MODELS_DIR:-$HOME/.cache/daily-morning-news/models}"
FONT="${FONT_PATH:-}"
if [ -z "$FONT" ]; then
  for candidate in /System/Library/Fonts/PingFang.ttc /usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc; do
    if [ -f "$candidate" ]; then FONT="$candidate"; break; fi
  done
fi
[ -f "$FONT" ] || { echo "Set FONT_PATH to a valid CJK font" >&2; exit 1; }
exec python3 "$HERE/run_illustrated.py" "$DIR" --models "$MODELS" --font "$FONT"
