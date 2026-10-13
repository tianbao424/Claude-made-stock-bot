"""逐句合成标准普通话旁白：输出 build/narration.wav、build/timeline.json、build/subtitles.srt。

用法: python3 synth.py <report_dir> <models_dir>
同一句朗读文本的音频按 md5 缓存在 build/cache/，改稿后只重合成改动的句子。
"""
import hashlib
import json
import os
import sys

import numpy as np
import sherpa_onnx
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
# 引擎会丢弃英文字母和部分标点：朗读前替换（"诶股""诶爱"的读音在 lexicon_extra.txt 里固定）
SAY_REPLACE = [("AI", "诶爱"), ("A股", "诶股"), ("；", "，"), ("·", "")]
SENT_GAP, SLIDE_GAP, HEAD, TAIL = 0.28, 0.65, 0.5, 0.8


def prepare_say(say):
    for old, new in SAY_REPLACE:
        say = say.replace(old, new)
    return say


def load_extra_lexicon(rep):
    lines = [l.strip() for l in open(os.path.join(HERE, "lexicon_extra.txt"), encoding="utf8")
             if l.strip() and not l.startswith("#")]
    return lines + [l.strip() for l in rep.get("lexicon_extra", []) if l.strip()]


def merged_lexicon(model_dir, extra, out_path):
    keys = {l.split()[0] for l in extra}
    base = [l for l in open(os.path.join(model_dir, "lexicon.txt"), encoding="utf8")
            if l.split() and l.split()[0] not in keys]
    with open(out_path, "w", encoding="utf8") as f:
        f.write("\n".join(extra) + "\n" + "".join(base))
    return out_path


def make_tts(models, lex_path):
    z = os.path.join(models, "matcha-icefall-zh-baker")
    return sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            matcha=sherpa_onnx.OfflineTtsMatchaModelConfig(
                acoustic_model=f"{z}/model-steps-3.onnx", vocoder=f"{models}/vocos-22khz-univ.onnx",
                lexicon=lex_path, tokens=f"{z}/tokens.txt", dict_dir=f"{z}/dict"),
            num_threads=4),
        rule_fsts=f"{z}/phone.fst,{z}/date.fst,{z}/number.fst",
        max_num_sentences=1))


def srt_ts(s):
    h, r = divmod(s, 3600); m, r = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(r):02d},{int(round((r % 1) * 1000)) % 1000:03d}"


def main():
    rdir, models = sys.argv[1], sys.argv[2]
    build = os.path.join(rdir, "build"); cache = os.path.join(build, "cache")
    os.makedirs(cache, exist_ok=True)
    rep = json.load(open(os.path.join(rdir, "report.json"), encoding="utf8"))
    extra = load_extra_lexicon(rep)
    lex = merged_lexicon(os.path.join(models, "matcha-icefall-zh-baker"), extra, os.path.join(build, "lexicon.merged.txt"))
    tts = None
    sr, chunks, timeline, t = 22050, [], [], HEAD
    for si, sl in enumerate(rep["slides"]):
        sents = sl["sentences"]
        for j, s in enumerate(sents):
            say = prepare_say(s["say"])
            key = hashlib.md5(("|".join(extra) + "||" + say).encode()).hexdigest()
            cp = os.path.join(cache, key + ".wav")
            if os.path.exists(cp):
                x, sr = sf.read(cp, dtype="float32")
            else:
                if tts is None:
                    tts = make_tts(models, lex)
                a = tts.generate(say, sid=0, speed=1.0)
                sr = a.sample_rate
                x = np.asarray(a.samples, dtype=np.float32)
                x = x / max(1e-6, np.abs(x).max()) * 0.89   # 峰值归一化
                sf.write(cp, x, sr)
            dur = len(x) / sr
            timeline.append({"slide": si, "idx": j, "sub": s["sub"], "clip": cp, "start": t, "end": t + dur})
            chunks.append((t, x))
            t += dur + (SENT_GAP if j < len(sents) - 1 else SLIDE_GAP)
    total = t - SLIDE_GAP + TAIL
    buf = np.zeros(int(total * sr) + 1, dtype=np.float32)
    for st, x in chunks:
        i = int(st * sr); buf[i:i + len(x)] += x
    sf.write(os.path.join(build, "narration.wav"), buf, sr)
    # 每句的显示区间：从本句开始到下一句开始（最后一句到片尾），画面不留空档
    for k, e in enumerate(timeline):
        e["show_end"] = timeline[k + 1]["start"] if k + 1 < len(timeline) else total
    json.dump({"total": total, "sr": sr, "items": timeline},
              open(os.path.join(build, "timeline.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
    with open(os.path.join(build, "subtitles.srt"), "w", encoding="utf8") as f:
        for k, e in enumerate(timeline, 1):
            f.write(f"{k}\n{srt_ts(e['start'])} --> {srt_ts(e['end'])}\n{e['sub']}\n\n")
    print(f"{len(timeline)} sentences, total {total:.1f}s")


if __name__ == "__main__":
    main()
