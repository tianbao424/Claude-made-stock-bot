#!/usr/bin/env bash
# 安装依赖并下载离线语音模型（约 350MB，放在仓库外的缓存目录，不提交）。
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
# Bilingual English /eɪ/ + Chinese; no homophone substitution for A股.
if [ ! -f "$MODELS/kokoro-multi-lang-v1_1/model.onnx" ]; then
  fetch "$REL/tts-models/kokoro-multi-lang-v1_1.tar.bz2" "$MODELS/kokoro.tar.bz2"
  tar xjf "$MODELS/kokoro.tar.bz2" -C "$MODELS" && rm "$MODELS/kokoro.tar.bz2"
fi
(cd "$MODELS" && sha256sum -c "$HERE/kokoro-v1.1.sha256")
if [ "${1:-}" = "--with-asr" ] && [ ! -f "$MODELS/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/model.int8.onnx" ]; then
  fetch "$REL/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17.tar.bz2" "$MODELS/asr.tar.bz2"
  tar xjf "$MODELS/asr.tar.bz2" -C "$MODELS" && rm "$MODELS/asr.tar.bz2"
fi
echo "模型目录: $MODELS"
