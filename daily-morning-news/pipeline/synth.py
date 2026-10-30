"""逐句合成标准普通话旁白：输出 build/narration.wav、build/timeline.json、build/subtitles.srt。

用法: python3 synth.py <report_dir> <models_dir>
音频按文本、模型内容、引擎版本、语速和裁剪配置的 SHA256 缓存。
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
import sys

import numpy as np
import sherpa_onnx
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
# 仅旧版 Matcha 引擎：朗读前替换（"诶股""诶爱"的读音在 lexicon_extra.txt 里固定）
SAY_REPLACE = [("AI", "诶爱"), ("A股", "诶股"), ("；", "，"), ("·", "")]
SENT_GAP, SLIDE_GAP, HEAD, TAIL = 0.15, 0.35, 0.3, 0.5
CACHE_VERSION = 3
KOKORO_ALIAS = "ashareletter"
KOKORO_LEXICON = [f"{KOKORO_ALIAS} ˈ A"]
TRIM_DB, TRIM_PAD = -50.0, 0.04


def prepare_say(say, engine="matcha"):
    replacements = SAY_REPLACE if engine == "matcha" else [("A股", KOKORO_ALIAS + "股"), ("；", "，"), ("·", "")]
    for old, new in replacements:
        say = say.replace(old, new)
    return say


def load_extra_lexicon(rep):
    with open(os.path.join(HERE, "lexicon_extra.txt"), encoding="utf8") as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
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


def kokoro_lexicon(models, build):
    source = os.path.join(models, "kokoro-multi-lang-v1_1", "lexicon-us-en.txt")
    target = os.path.join(build, "lexicon.kokoro-en.txt")
    with open(source, encoding="utf8") as f:
        base = [line for line in f if line.split() and line.split()[0] != KOKORO_ALIAS]
    with open(target, "w", encoding="utf8") as f:
        f.write("\n".join(KOKORO_LEXICON) + "\n" + "".join(base))
    return target


def make_kokoro(models, lex_path):
    z = os.path.join(models, "kokoro-multi-lang-v1_1")
    config = sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
        kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
            model=f"{z}/model.onnx", voices=f"{z}/voices.bin", tokens=f"{z}/tokens.txt",
            lexicon=f"{lex_path},{z}/lexicon-zh.txt"),
        num_threads=4), max_num_sentences=1)
    if not config.validate():
        raise ValueError("Invalid Kokoro model configuration")
    return sherpa_onnx.OfflineTts(config)


def srt_ts(s):
    ms = round(s * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def trim_edges(x, sr, db=TRIM_DB, pad=TRIM_PAD):
    """Only remove edge silence; retain quiet consonants and all internal pauses."""
    x = np.asarray(x, dtype=np.float32)
    if x.ndim != 1 or not len(x) or not np.isfinite(x).all():
        raise ValueError("Expected finite, nonempty mono audio")
    peak = float(np.max(np.abs(x)))
    if peak < 1e-6:
        raise ValueError("TTS produced silent audio")
    active = np.flatnonzero(np.abs(x) > max(1e-6, peak * 10 ** (db / 20)))
    margin = round(pad * sr)
    start, end = max(0, int(active[0]) - margin), min(len(x), int(active[-1]) + 1 + margin)
    return x[start:end], {"removed_head": start / sr, "removed_tail": (len(x) - end) / sr}


def file_digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def model_digest(root):
    # Contents, not mtimes: replacing a model or dictionary invalidates the cache.
    from pathlib import Path
    return {str(p.relative_to(root)): file_digest(p) for p in sorted(Path(root).rglob("*"))
            if p.is_file() and not p.name.endswith((".tar.bz2", ".part"))}


def cache_key(say, config):
    return hashlib.sha256(json.dumps({"say": say, "config": config}, sort_keys=True,
                                    ensure_ascii=False).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report_dir")
    parser.add_argument("models_dir")
    parser.add_argument("--engine", choices=["matcha", "kokoro"], default="kokoro")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--sid", type=int, default=None)
    args = parser.parse_args()
    if not 0.5 <= args.speed <= 2:
        parser.error("--speed must be between 0.5 and 2")
    if args.sid is None:
        args.sid = 3 if args.engine == "kokoro" else 0
    rdir, models = args.report_dir, args.models_dir
    build = os.path.join(rdir, "build"); cache = os.path.join(build, "cache")
    os.makedirs(cache, exist_ok=True)
    with open(os.path.join(rdir, "report.json"), encoding="utf8") as f:
        rep = json.load(f)
    extra = load_extra_lexicon(rep)
    lex = (merged_lexicon(os.path.join(models, "matcha-icefall-zh-baker"), extra,
                          os.path.join(build, "lexicon.merged.txt")) if args.engine == "matcha" else kokoro_lexicon(models, build))
    config = {"version": CACHE_VERSION, "engine": args.engine,
              "engine_version": importlib.metadata.version("sherpa-onnx"),
              "models": model_digest(os.path.join(models, "kokoro-multi-lang-v1_1")) if args.engine == "kokoro" else model_digest(models), "lexicon": extra if args.engine == "matcha" else KOKORO_LEXICON,
              "speed": args.speed, "sid": args.sid, "trim_db": TRIM_DB, "trim_pad": TRIM_PAD,
              "sentence_gap": SENT_GAP, "slide_gap": SLIDE_GAP, "head": HEAD, "tail": TAIL}
    tts = None
    sr, chunks, timeline, t = 22050, [], [], HEAD
    for si, sl in enumerate(rep["slides"]):
        sents = sl["sentences"]
        for j, s in enumerate(sents):
            say = prepare_say(s["say"], args.engine)
            key = cache_key(say, config)
            cp = os.path.join(cache, key + ".wav")
            meta_path = cp + ".json"
            trim = None
            if os.path.exists(cp):
                if os.path.exists(meta_path):
                    with open(meta_path, encoding="utf8") as f:
                        trim = json.load(f)
                x, clip_sr = sf.read(cp, dtype="float32")
            else:
                if tts is None:
                    tts = make_tts(models, lex) if args.engine == "matcha" else make_kokoro(models, lex)
                a = tts.generate(say, sid=args.sid, speed=args.speed)
                clip_sr = a.sample_rate
                x = np.asarray(a.samples, dtype=np.float32)
                x, trim = trim_edges(x, clip_sr)
                x = x / max(1e-6, np.abs(x).max()) * 0.89   # 峰值归一化
                sf.write(cp, x, clip_sr)
                with open(meta_path, "w", encoding="utf8") as f:
                    json.dump(trim, f)
                # Read quantized cache bytes on first run too, for reproducibility.
                x, clip_sr = sf.read(cp, dtype="float32")
            if x.ndim != 1 or not len(x) or not np.isfinite(x).all() or np.max(np.abs(x)) < 1e-6:
                raise ValueError(f"Invalid cached audio: {cp}; remove it and rerun")
            if not chunks:
                sr = clip_sr
            elif clip_sr != sr:
                raise ValueError("Mixed sample rates in sentence cache")
            dur = len(x) / sr
            timeline.append({"slide": si, "idx": j, "sub": s["sub"], "clip": cp, "trim": trim, "start": t, "end": t + dur})
            chunks.append((t, x))
            t += dur + (SENT_GAP if j < len(sents) - 1 else SLIDE_GAP)
    if not timeline:
        raise ValueError("Report must contain at least one sentence")
    total = t - SLIDE_GAP + TAIL
    buf = np.zeros(int(total * sr) + 1, dtype=np.float32)
    for st, x in chunks:
        i = int(st * sr); buf[i:i + len(x)] += x
    sf.write(os.path.join(build, "narration.wav"), buf, sr)
    # 每句的显示区间：从本句开始到下一句开始（最后一句到片尾），画面不留空档
    for k, e in enumerate(timeline):
        e["show_end"] = timeline[k + 1]["start"] if k + 1 < len(timeline) else total
    with open(os.path.join(build, "timeline.json"), "w", encoding="utf8") as f:
        json.dump({"total": total, "sr": sr, "config": config, "items": timeline}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(build, "subtitles.srt"), "w", encoding="utf8") as f:
        for k, e in enumerate(timeline, 1):
            f.write(f"{k}\n{srt_ts(e['start'])} --> {srt_ts(e['end'])}\n{e['sub']}\n\n")
    print(f"{len(timeline)} sentences, total {total:.1f}s")


if __name__ == "__main__":
    main()
