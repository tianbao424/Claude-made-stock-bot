#!/usr/bin/env python3
"""回听关键词：用离线 ASR 识别含「美股」「港股」的句子，没识别出来的删掉缓存音频，
由下一次 make_video.sh 重新合成（TTS 每次合成有随机性）。
「美股」按变调读 mei2 gu3，识别成「煤股」也算正确。
用法: python3 asr_recheck.py <report_dir> [models_dir]
输出最后一行 "bad N"；N>0 时重跑 make_video.sh 再执行本脚本，最多 3 轮。"""
import json, os, sys
import numpy as np, soundfile as sf, sherpa_onnx

d = sys.argv[1]
models = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser("~/.cache/daily-morning-news/models")
m = os.path.join(models, "sherpa-onnx-paraformer-zh-small-2024-03-09")
if not os.path.isdir(m):
    sys.exit("缺 ASR 模型，先运行: bash pipeline/setup.sh --with-asr")
asr = sherpa_onnx.OfflineRecognizer.from_paraformer(paraformer=m + "/model.int8.onnx", tokens=m + "/tokens.txt")
OK = {"美股": ("美股", "煤股"), "港股": ("港股",)}
bad = 0
for it in json.load(open(os.path.join(d, "build", "timeline.json")))["items"]:
    keys = [k for k in OK if k in it["sub"]]
    if not keys:
        continue
    s, sr = sf.read(it["clip"], dtype="float32")
    s16 = np.interp(np.arange(0, len(s), sr / 16000), np.arange(len(s)), s).astype(np.float32)
    st = asr.create_stream(); st.accept_waveform(16000, s16); asr.decode_stream(st)
    text = st.result.text
    if not all(any(v in text for v in OK[k]) for k in keys):
        os.remove(it["clip"]); bad += 1
        print("重合成:", it["sub"], "→ 识别为", text)
print("bad", bad)
