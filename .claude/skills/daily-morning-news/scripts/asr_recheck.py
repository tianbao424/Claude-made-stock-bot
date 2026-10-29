#!/usr/bin/env python3
"""Read-only bilingual keyword regression check; never delete audio/cache.

Usage: asr_recheck.py <report_dir> [models_dir]
ASR is diagnostic evidence, not human listening or full-content validation.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import soundfile as sf
import sherpa_onnx


def main():
    report = Path(sys.argv[1]).resolve()
    models = Path(sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser("~/.cache/daily-morning-news/models"))
    model = models / "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17"
    if not (model / "model.int8.onnx").is_file():
        sys.exit("缺少 SenseVoice ASR：请运行 bash pipeline/setup.sh --with-asr")
    asr = sherpa_onnx.OfflineRecognizer.from_sense_voice(
        model=str(model / "model.int8.onnx"), tokens=str(model / "tokens.txt"),
        num_threads=4, language="zh", use_itn=True)
    # Mandarin homophones do not indicate wrong sound. A股 must retain the
    # English letter, rather than accepting arbitrary Chinese approximations.
    accepted = {"A股": ("A股", "a股"), "美股": ("美股", "煤股", "每股"), "港股": ("港股",)}
    timeline = json.loads((report / "build/timeline.json").read_text())
    rows = []
    for item in timeline["items"]:
        keys = [key for key in accepted if key in item["sub"]]
        if not keys:
            continue
        clip = Path(item["clip"])
        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "resampled.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-i", str(clip), "-ar", "16000", "-ac", "1", str(wav)], check=True)
            samples, sr = sf.read(wav, dtype="float32")
        stream = asr.create_stream()
        stream.accept_waveform(sr, samples)
        asr.decode_stream(stream)
        text = stream.result.text
        passed = all(any(v in text.replace(" ", "") for v in accepted[key]) for key in keys)
        rows.append({"slide": item["slide"], "idx": item["idx"], "sub": item["sub"],
                     "keywords": keys, "asr": text, "passed": passed,
                     "clip_sha256": hashlib.sha256(clip.read_bytes()).hexdigest()})
        print("通过:" if passed else "需复核:", item["sub"], "→", text)
    bad = sum(not row["passed"] for row in rows)
    result = {"read_only_audio": True, "human_listening_confirmed": False,
              "checked": len(rows), "bad": bad, "items": rows}
    (report / "build/asr-keywords.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print("checked", len(rows))
    print("bad", bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
