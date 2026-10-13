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

OUT="$DIR/morning_news_$DATE.mp4"
INTRO="${INTRO_VIDEO:-$HERE/assets/intro.mp4}"   # 片头；设 INTRO_VIDEO= 为空可跳过
ENC=(-c:v libx264 -preset medium -crf 28 -g 450 -c:a aac -b:a 64k -ac 1 -ar 44100 -movflags +faststart)
ffmpeg -y -loglevel error -f concat -safe 0 -i "$DIR/build/frames.txt" -i "$DIR/build/narration.wav" \
  -vf "fps=15,format=yuv420p" -tune stillimage "${ENC[@]}" -shortest "$DIR/build/main.mp4"
ffmpeg -y -loglevel error -i "$DIR/build/narration.wav" -ac 1 -ar 44100 -c:a libmp3lame -b:a 64k "$DIR/narration.mp3"
if [ -n "$INTRO" ] && [ -f "$INTRO" ]; then
  # 片头统一成正片规格（1080x1920、15fps、单声道 44.1kHz）后拼接，字幕整体后移片头时长
  ffmpeg -y -loglevel error -i "$INTRO" -i "$DIR/build/main.mp4" -filter_complex \
    "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,fps=15,setsar=1,format=yuv420p[iv];\
     [0:a]aformat=sample_rates=44100:channel_layouts=mono[ia];[1:a]aformat=sample_rates=44100:channel_layouts=mono[ma];\
     [iv][ia][1:v][ma]concat=n=2:v=1:a=1[v][a]" -map "[v]" -map "[a]" "${ENC[@]}" "$OUT"
  OFFSET=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$INTRO")
  python3 - "$DIR/build/subtitles.srt" "$DIR/subtitles.srt" "$OFFSET" <<'PY'
import re, sys
src, dst, off = sys.argv[1], sys.argv[2], float(sys.argv[3])
def shift(m):
    t = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3]) + int(m[4]) / 1000 + off
    ms = round(t * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
txt = open(src, encoding="utf8").read()
open(dst, "w", encoding="utf8").write(re.sub(r"(\d+):(\d+):(\d+),(\d+)", shift, txt))
PY
else
  cp "$DIR/build/main.mp4" "$OUT"
  cp "$DIR/build/subtitles.srt" "$DIR/subtitles.srt"
fi

ffprobe -v error -show_entries format=duration,size -of compact=p=0 "$OUT"
echo "完成: $DIR/morning_news_$DATE.mp4"
