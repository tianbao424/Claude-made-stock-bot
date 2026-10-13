#!/usr/bin/env python3
"""合成原创背景音乐 assets/bgm.mp3：法国香颂 / musette 风格的手风琴华尔兹（纯音乐，无版权问题）。
3/4 拍，D 小调 → F 大调 → D 小调，约 36 秒一循环，make_video.sh 会循环铺满全片并压在人声下。
用法: python3 make_bgm.py [输出路径]"""
import os, subprocess, sys, tempfile
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "assets", "bgm.mp3")
SR = 44100
BPM = 168
BEAT = 60 / BPM
BAR = 3 * BEAT

NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}
NOTE.update({"Db": 1, "Eb": 3, "Gb": 6, "Ab": 8, "Bb": 10})


def hz(name):  # "A4" / "Bb3"
    n, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((NOTE[n] + 12 * (o + 1) - 69) / 12)


# 和弦：低音根音 / 五音，以及第二、三拍的和弦音
CHORDS = {
    "Dm": (["D2", "A2"], ["D4", "F4", "A4"]), "A7": (["A2", "E2"], ["C#4", "E4", "G4"]),
    "Gm": (["G2", "D2"], ["D4", "G4", "Bb4"]), "F": (["F2", "C2"], ["C4", "F4", "A4"]),
    "C7": (["C2", "G2"], ["C4", "E4", "Bb4"]), "Bb": (["Bb1", "F2"], ["D4", "F4", "Bb4"]),
    "D7": (["D2", "A2"], ["C4", "D4", "F#4"]),
}
PROG = ("Dm Dm A7 A7 A7 A7 Dm Dm Gm Gm Dm Dm A7 A7 Dm Dm "
        "F F C7 C7 C7 C7 F F Bb Bb F D7 Gm A7 Dm Dm").split()

# 旋律：每小节若干 (音, 拍数)，"-" 为休止。A 段带一点忧郁，B 段转明亮
MEL = [
    [("A4", 1), ("D5", 1), ("E5", 1)], [("F5", 2), ("E5", 1)], [("E5", 1), ("C#5", 1), ("E5", 1)], [("G5", 3)],
    [("G5", 1), ("F5", 0.5), ("E5", 0.5), ("D5", 1)], [("C#5", 2), ("E5", 1)], [("D5", 1), ("A4", 1), ("D5", 1)], [("F5", 3)],
    [("Bb4", 1), ("D5", 1), ("G5", 1)], [("Bb5", 2), ("A5", 1)], [("A5", 1), ("F5", 1), ("D5", 1)], [("A5", 3)],
    [("G5", 1), ("F5", 0.5), ("E5", 0.5), ("C#5", 1)], [("E5", 1), ("D5", 1), ("C#5", 1)], [("D5", 3)], [("-", 2), ("C5", 1)],
    [("F5", 1), ("A5", 1), ("C6", 1)], [("A5", 2), ("F5", 1)], [("E5", 1), ("G5", 1), ("Bb5", 1)], [("G5", 3)],
    [("G5", 1), ("Bb5", 0.5), ("A5", 0.5), ("G5", 1)], [("E5", 2), ("C5", 1)], [("F5", 1), ("C5", 1), ("F5", 1)], [("A5", 3)],
    [("Bb5", 1), ("A5", 0.5), ("G5", 0.5), ("F5", 1)], [("D5", 2), ("F5", 1)], [("A5", 1), ("G5", 0.5), ("F5", 0.5), ("E5", 1)],
    [("F#5", 2), ("A5", 1)], [("G5", 1), ("Bb5", 1), ("D5", 1)], [("E5", 1), ("C#5", 1), ("A4", 1)], [("D5", 3)], [("-", 3)],
]
assert len(MEL) == len(PROG)


def env(n, a=0.02, r=0.08):
    e = np.ones(n)
    na, nr = min(int(a * SR), n), min(int(r * SR), n)
    e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def accordion(f, dur, vol):
    """手风琴：两组簧片轻微失谐产生 musette 颤音 + 风箱轻微起伏。"""
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.zeros(n)
    for detune in (-0.0035, 0.0035):
        ff = f * (1 + detune)
        for h, amp in ((1, 1.0), (2, 0.55), (3, 0.38), (4, 0.22), (5, 0.15), (6, 0.08)):
            sig += amp * np.sin(2 * np.pi * ff * h * t)
    sig *= 1 + 0.06 * np.sin(2 * np.pi * 5.2 * t)
    return sig / 5.0 * vol * env(n, 0.025, 0.07)


def bass(f, dur, vol):
    """拨弦低音：快速衰减。"""
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t)
    return sig * np.exp(-t * 5) * vol * env(n, 0.005, 0.05)


def add(buf, start, sig):
    i = int(start * SR)
    buf[i:i + len(sig)] += sig[:max(0, len(buf) - i)]


def main():
    total = len(PROG) * BAR
    buf = np.zeros(int(total * SR) + SR)
    for b, (ch, mel) in enumerate(zip(PROG, MEL)):
        t0 = b * BAR
        lows, tones = CHORDS[ch]
        add(buf, t0, bass(hz(lows[b % 2]), BEAT * 0.95, 0.55))            # 嘭
        for k in (1, 2):                                                   # 嚓 嚓
            for nm in tones:
                add(buf, t0 + k * BEAT, accordion(hz(nm), BEAT * 0.45, 0.16))
        t = t0
        for nm, beats in mel:
            if nm != "-":
                add(buf, t, accordion(hz(nm), beats * BEAT * 0.97, 0.42))
            t += beats * BEAT
    buf = buf[:int(total * SR)]
    # 简单的房间混响：几路衰减延迟
    wet = np.zeros_like(buf)
    for d, g in ((0.031, 0.32), (0.053, 0.24), (0.079, 0.18), (0.113, 0.12)):
        k = int(d * SR); wet[k:] += buf[:-k] * g
    buf = buf + wet
    # 首尾交叉淡化，循环拼接时无缝
    x = int(0.25 * SR)
    buf[:x] *= np.linspace(0, 1, x); buf[-x:] *= np.linspace(1, 0, x)
    buf = buf / np.abs(buf).max() * 0.85
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "bgm.wav")
        sf.write(wav, buf.astype(np.float32), SR)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-ac", "1",
                        "-c:a", "libmp3lame", "-b:a", "96k", OUT], check=True)
    print(f"BGM: {OUT}  {total:.1f}s")


if __name__ == "__main__":
    main()
