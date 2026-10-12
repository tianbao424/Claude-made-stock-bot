#!/usr/bin/env bash
# 安装依赖并下载离线语音模型（约 130MB，放在仓库外的缓存目录，不提交）。
# 用法: bash setup.sh [--with-asr]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
MODELS="${MODELS_DIR:-$HOME/.cache/daily-morning-news/models}"
REL="https://github.com/k2-fsa/sherpa-onnx/releases/download"

# jieba 只有 setup.py，用 PEP 517 构建以避开系统自带旧版 setuptools
pip install -q --use-pep517 -r "$HERE/requirements.txt"
command -v ffmpeg >/dev/null || { echo "缺少 ffmpeg" >&2; exit 1; }

mkdir -p "$MODELS"
fetch() {  # fetch <url> <dest>，失败按 2/4/8/16 秒退避重试
  local url="$1" dest="$2" n=0
  until curl -fsSL -m 600 -o "$dest.part" "$url"; do
    n=$((n + 1)); [ "$n" -ge 5 ] && { echo "下载失败: $url" >&2; return 1; }
    sleep $((2 ** n))
  done
  mv "$dest.part" "$dest"
}
if [ ! -f "$MODELS/matcha-icefall-zh-baker/model-steps-3.onnx" ]; then
  fetch "$REL/tts-models/matcha-icefall-zh-baker.tar.bz2" "$MODELS/baker.tar.bz2"
  tar xjf "$MODELS/baker.tar.bz2" -C "$MODELS" && rm "$MODELS/baker.tar.bz2"
fi
[ -f "$MODELS/vocos-22khz-univ.onnx" ] || fetch "$REL/vocoder-models/vocos-22khz-univ.onnx" "$MODELS/vocos-22khz-univ.onnx"
if [ "${1:-}" = "--with-asr" ] && [ ! -d "$MODELS/sherpa-onnx-paraformer-zh-small-2024-03-09" ]; then
  fetch "$REL/asr-models/sherpa-onnx-paraformer-zh-small-2024-03-09.tar.bz2" "$MODELS/asr.tar.bz2"
  tar xjf "$MODELS/asr.tar.bz2" -C "$MODELS" && rm "$MODELS/asr.tar.bz2"
fi
echo "模型目录: $MODELS"
