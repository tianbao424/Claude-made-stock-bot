#!/usr/bin/env bash
# 从 report.json 生成配音、字幕和竖屏视频。
# 用法: bash make_video.sh <report_dir>      例: bash make_video.sh reports/2026-10-12
# 产出（在 report_dir 下）: morning_news_<日期>.mp4  narration.mp3  subtitles.srt
# 中间文件在 report_dir/build/（已被 .gitignore 忽略）
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DIR="${1:?用法: make_video.sh <report_dir>}"
MODELS="${MODELS_DIR:-$HOME/.cache/daily-morning-news/models}"
DATE="$(basename "$DIR")"

python3 "$HERE/lint_say.py" "$DIR/report.json" "$MODELS"
python3 "$HERE/synth.py" "$DIR" "$MODELS"
python3 "$HERE/render.py" "$DIR"

ffmpeg -y -loglevel error -f concat -safe 0 -i "$DIR/build/frames.txt" -i "$DIR/build/narration.wav" \
  -vf "fps=15,format=yuv420p" -c:v libx264 -preset medium -crf 28 -tune stillimage -g 450 \
  -c:a aac -b:a 64k -ac 1 -ar 44100 -movflags +faststart -shortest "$DIR/morning_news_$DATE.mp4"
ffmpeg -y -loglevel error -i "$DIR/build/narration.wav" -ac 1 -ar 44100 -c:a libmp3lame -b:a 64k "$DIR/narration.mp3"
cp "$DIR/build/subtitles.srt" "$DIR/subtitles.srt"

ffprobe -v error -show_entries format=duration,size -of compact=p=0 "$DIR/morning_news_$DATE.mp4"
echo "完成: $DIR/morning_news_$DATE.mp4"
