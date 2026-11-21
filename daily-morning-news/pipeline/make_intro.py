#!/usr/bin/env python3
"""生成片头 assets/intro.mp4：K线逐根升起、金色走势线划过，标题落在开场页标题的位置后切入正片。
不含日期和行情数字，生成一次即可长期复用。用法: python3 make_intro.py [输出路径]"""
import os, subprocess, sys, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import W, H, C, F, background, bold  # 与正片同一套字体、配色

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "assets", "intro.mp4")
FPS, DUR = 30, 4.5
TITLE, TAG = "股市早报", "美股 · A股 · 港股  |  开盘前三分钟"

# 一段先抑后扬、收在高位的走势（手工设定，保证每次生成一致）
closes = np.array([100, 103, 101, 98, 99, 96, 94, 97, 95, 99, 102, 100, 104, 107, 105, 109, 112, 110, 114, 118, 116, 121.0])
N = len(closes)
opens = np.r_[closes[0] - 2, closes[:-1]]
lo_v, hi_v = min(opens.min(), closes.min()) - 3, max(opens.max(), closes.max()) + 3
X0, X1, Y0, Y1 = 90, 990, 1560, 900          # 图表区域（Y0 在下）
xs = np.linspace(X0 + 20, X1 - 20, N)
ymap = lambda v: Y0 - (v - lo_v) / (hi_v - lo_v) * (Y0 - Y1)


def ease(t):  # 0..1 缓入缓出
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def seg(t, a, b):
    return ease((t - a) / (b - a))


BG = background()


def frame(t):
    chart_a = 1 - seg(t, 3.6, 4.3)               # 结尾淡出图表，只留与开场页一致的标题
    img = BG.copy()
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for y in range(Y1 - 40, Y0 + 41, 100):  # 网格随图表一起淡出
        d.line([(X0, y), (X1, y)], fill=(42, 64, 104, int(110 * chart_a)), width=2)
    # K 线逐根升起
    for i in range(N):
        p = seg(t, 0.15 + i * 0.06, 0.45 + i * 0.06)
        if p <= 0:
            continue
        o, c = opens[i], closes[i]
        col = C["up"] if c >= o else C["down"]
        a = int(255 * 0.55 * p * chart_a)
        rgb = tuple(int(col[k:k + 2], 16) for k in (1, 3, 5))
        top, bot = ymap(max(o, c)), ymap(min(o, c))
        mid = (top + bot) / 2
        top, bot = mid - (mid - top) * p, mid + (bot - mid) * p
        d.line([(xs[i], top - 18 * p), (xs[i], bot + 18 * p)], fill=rgb + (a,), width=3)
        d.rectangle([xs[i] - 15, top, xs[i] + 15, max(bot, top + 3)], fill=rgb + (a,))
    # 金色走势线划过
    p = seg(t, 0.6, 2.4)
    if p > 0:
        k = max(2, int(p * (N - 1) * 8) + 1)
        fx = np.linspace(xs[0], xs[0] + (xs[-1] - xs[0]) * p, k)
        pts = list(zip(fx, np.interp(fx, xs, [ymap(v) for v in closes])))
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).line(pts, fill=(245, 184, 65, int(150 * chart_a)), width=18, joint="curve")
        layer.alpha_composite(glow.filter(ImageFilter.GaussianBlur(10)))
        d.line(pts, fill=(245, 184, 65, int(255 * chart_a)), width=6, joint="curve")
        ex, ey = pts[-1]
        d.ellipse([ex - 11, ey - 11, ex + 11, ey + 11], fill=(255, 255, 255, int(255 * chart_a)))
    img = Image.alpha_composite(img.convert("RGBA"), layer)

    # 标题从下方滑入，终点与开场页标题完全一致（y=470、150 号字、金色短线 670）
    txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    td = ImageDraw.Draw(txt)
    pt = seg(t, 0.5, 1.5)
    if pt > 0:
        bold(td, (W / 2, 470 + 60 * (1 - pt)), TITLE, F(150), C["text"], "mm", 3)
        txt.putalpha(txt.getchannel("A").point(lambda v: int(v * pt)))
    img = Image.alpha_composite(img, txt)
    d = ImageDraw.Draw(img)
    pl = seg(t, 1.2, 1.9)
    if pl > 0:
        d.rectangle([W / 2 - 80 * pl, 670, W / 2 + 80 * pl, 676], fill=C["gold"])
    ptag = seg(t, 1.6, 2.3) * (1 - seg(t, 3.7, 4.3))   # 标语在日期的位置，切入正片前淡出
    if ptag > 0:
        g = tuple(int(C["sub"][k:k + 2], 16) for k in (1, 3, 5))
        bg = (14, 22, 42)
        col = tuple(int(bg[j] + (g[j] - bg[j]) * ptag) for j in range(3))
        d.text((W / 2, 610), TAG, font=F(44), fill=col, anchor="mm")
    return img.convert("RGB")


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for n in range(int(FPS * DUR)):
            frame(n / FPS).save(os.path.join(tmp, f"{n:04d}.png"))
        # 轻柔的上行三音提示音（C5-E5-G5），末尾淡出
        chime = ("0.18*sin(2*PI*523.25*t)*exp(-3*t)"
                 "+0.15*sin(2*PI*659.25*t)*exp(-3*(t-0.35))*gt(t,0.35)"
                 "+0.13*sin(2*PI*783.99*t)*exp(-2.5*(t-0.7))*gt(t,0.7)")
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(tmp, "%04d.png"),
            "-f", "lavfi", "-t", str(DUR), "-i", f"aevalsrc='{chime}':s=44100:c=mono",
            "-af", f"afade=t=out:st={DUR - 1.2}:d=1.2", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "64k", "-shortest", "-movflags", "+faststart", OUT,
        ], check=True)
    print("片头:", OUT)


if __name__ == "__main__":
    main()
