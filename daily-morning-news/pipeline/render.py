"""按 report.json + build/timeline.json 逐句渲染竖屏画面（1080x1920），输出 ffmpeg concat 清单和检查用拼图。

用法: python3 render.py <report_dir>
"""
import json
import os
import subprocess
import sys
from itertools import combinations

import jieba
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
C = dict(text="#F3F6FB", sub="#9AA8C1", card="#16233D", card_hi="#1F365A", gold="#F5B841",
         up="#FF4D4F", down="#2FD07A", line="#2A3B5C", dim="#C9D3E5")
# 情绪四档（market-sentiment skill 的 hot/warm/neutral/cool）
ST = dict(hot=("过热", "#E5487A"), warm=("偏热", "#E39A2D"), neutral=("中性", "#56627A"), cool=("偏冷", "#1FA97F"))
UP, DOWN = "up", "down"


def find_font():
    cands = [os.environ.get("FONT_PATH", ""), "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]
    try:
        out = subprocess.run(["fc-list", ":lang=zh", "file"], capture_output=True, text=True).stdout
        cands += [l.split(":")[0] for l in out.splitlines()]
    except FileNotFoundError:
        pass
    for p in cands:
        if p and os.path.exists(p):
            return p
    sys.exit("找不到中文字体，请安装 fonts-wqy-zenhei 或设置 FONT_PATH")


FONT = find_font()
_fonts = {}
def F(size):
    if size not in _fonts:
        _fonts[size] = ImageFont.truetype(FONT, size)
    return _fonts[size]


def background():
    t = np.linspace(0, 1, H)[:, None]
    top, bot = np.array([10, 16, 32]), np.array([20, 34, 60])
    g = (top + (bot - top) * t[..., None]).astype(np.uint8)
    return Image.fromarray(np.repeat(g, W, axis=1), "RGB")


def bold(d, xy, s, font, fill, anchor="la", w=1):
    d.text(xy, s, font=font, fill=fill, anchor=anchor, stroke_width=w, stroke_fill=fill)


def tri(d, cx, cy, size, direction, fill):
    h = size * 0.9
    pts = [(cx - size / 2, cy + h / 2), (cx + size / 2, cy + h / 2), (cx, cy - h / 2)] if direction == UP else \
          [(cx - size / 2, cy - h / 2), (cx + size / 2, cy - h / 2), (cx, cy + h / 2)]
    d.polygon(pts, fill=fill)


def panel(d, box, on, r=22):
    d.rounded_rectangle(box, r, fill=C["card_hi"] if on else C["card"],
                        outline=C["gold"] if on else None, width=4 if on else 0)


# ---------- 公共元素 ----------

def header(d, rep):
    title = rep.get("title", "股市早报")
    bold(d, (60, 70), title, F(84), C["text"], w=2)
    d.text((60 + d.textlength(title, font=F(84)) + 24, 118), rep["date_display"], font=F(36), fill=C["sub"], anchor="ls")
    d.rectangle([60, 186, 1020, 190], fill=C["gold"])


def tabs(d, names, cur):
    x = 60
    for i, name in enumerate(names):
        f = F(36); tw = d.textlength(name, font=f); w = tw + 40
        if i == cur:
            d.rounded_rectangle([x, 222, x + w, 290], 34, fill=C["gold"]); bold(d, (x + w / 2, 256), name, f, "#10182B", "mm")
        else:
            d.rounded_rectangle([x, 222, x + w, 290], 34, outline=C["line"], width=3)
            d.text((x + w / 2, 256), name, font=f, fill=C["sub"], anchor="mm")
        x += w + 14


def pct_pill(d, x1, y, pct, dirn):
    col = C["up"] if dirn == UP else C["down"]
    f = F(46); tw = d.textlength(pct, font=f); w = tw + 82; x0 = x1 - w
    d.rounded_rectangle([x0, y - 38, x1, y + 38], 18, fill=col)
    tri(d, x0 + 32, y, 24, dirn, "#FFFFFF"); bold(d, (x1 - 22, y), pct, f, "#FFFFFF", "rm")


def rich(d, x, y, parts, size=40, on=False):
    for s, col in parts:
        fill = C.get(col, C["text"]) if col else (C["text"] if on else C["dim"])
        f = F(size); bold(d, (x, y), s, f, fill, "lm", 1 if (on or col in ("up", "down", "gold")) else 0)
        x += d.textlength(s, font=f)


def wrap(d, s, font, maxw):
    """宁可多一行，也优先在标点处断；各行尽量等长；不拆词、不拆数字、不在括号内断。"""
    tw = lambda t: d.textlength(t, font=font)
    if tw(s) <= maxw:
        return [s]
    punct = {i + 1 for i, ch in enumerate(s[:-1]) if ch in "，、；："}
    words, pos = set(), 0
    for w in jieba.cut(s):
        pos += len(w); words.add(pos)
    cands = sorted(i for i in (punct | words) - {len(s)} if s[i - 1] != "（" and s[i] not in "）的%")
    best = None
    for n in (2, 3, 4):
        for cut in combinations(cands, n - 1):
            parts = [s[i:j] for i, j in zip((0,) + cut, cut + (len(s),))]
            widths = [tw(x) for x in parts]
            if max(widths) > maxw:
                continue
            key = (sum(c not in punct for c in cut), n, max(widths))
            if best is None or key < best[0]:
                best = (key, parts)
        if best and (best[0][0] == 0 or n == 3):  # 超过 3 行会压到页脚，仅在 3 行放不下时才用 4 行
            break
    return best[1] if best else [s]


def subtitle(d, s):
    f = F(52); lines = wrap(d, s, f, 940); lh = 72
    h = len(lines) * lh + 44; y0 = 1560 - h / 2
    d.rounded_rectangle([50, y0, 1030, y0 + h], 26, fill="#000000A8")
    for i, l in enumerate(lines):
        bold(d, (W / 2, y0 + 22 + lh * i + lh / 2), l, f, "#FFFFFF", "mm", 1)


def asof_badge(d, text):
    """数据时点标签：金色描边，放在标签栏下方右侧，务必让观众看清数据是哪天的。"""
    f = F(28); tw = d.textlength(text, font=f)
    d.rounded_rectangle([1020 - tw - 36, 312, 1020, 356], 22, outline=C["gold"], width=2)
    d.text((1020 - 18, 334), text, font=f, fill=C["gold"], anchor="rm")


def footer(d, src):
    d.text((W / 2, 1712), src, font=F(28), fill=C["sub"], anchor="mm")
    d.text((W / 2, 1756), "仅供参考 · 不构成投资建议", font=F(28), fill=C["sub"], anchor="mm")


# ---------- 各类页面 ----------

def slide_intro(d, rep, sl, hi):
    bold(d, (W / 2, 470), rep.get("title", "股市早报"), F(150), C["text"], "mm", 3)
    d.text((W / 2, 610), rep.get("intro_date", rep["date_display"]), font=F(48), fill=C["sub"], anchor="mm")
    d.rectangle([W / 2 - 80, 670, W / 2 + 80, 676], fill=C["gold"])
    for i, (mkt, name, pct, dirn) in enumerate(sl["chips"]):
        y = 770 + i * 150; on = "chips" in hi
        panel(d, [110, y, 970, y + 120], on, 26)
        bold(d, (150, y + 60), mkt, F(48), C["gold"], "lm", 1)
        d.text((330, y + 60), name, font=F(44), fill=C["text"], anchor="lm")
        pct_pill(d, 940, y + 60, pct, dirn)
    # 数据时点说明：每期必须写明各市场数据对应的交易日
    note = rep.get("data_note", [])
    if note:
        y = 1212; h = 30 + 50 * len(note); on = "note" in hi
        d.rounded_rectangle([110, y, 970, y + h], 22, fill=C["card_hi"] if on else "#111C31",
                            outline=C["gold"], width=3 if on else 2)
        for i, (mkt, text) in enumerate(note):
            cy = y + 40 + i * 50
            bold(d, (146, cy), mkt, F(32), C["gold"], "lm", 1)
            d.text((330, cy), text, font=F(32), fill=C["text"], anchor="lm")


def slide_market(d, rep, sl, hi):
    y0, rh, gap = 380, 128, 18
    for i, (name, val, pct, dirn) in enumerate(sl["cards"]):
        y = y0 + i * (rh + gap); on = f"c{i}" in hi
        panel(d, [60, y, 1020, y + rh], on)
        cy = y + rh / 2
        bold(d, (92, cy), name, F(44), C["text"], "lm", 1 if on else 0)
        bold(d, (735, cy), val, F(54), C["text"], "rm", 1)
        pct_pill(d, 992, cy, pct, dirn)
    y = y0 + len(sl["cards"]) * (rh + gap) + 24; brh = 84
    for i, parts in enumerate(sl.get("bullets", [])):
        by = y + i * brh; on = f"b{i}" in hi
        if on:
            d.rounded_rectangle([60, by + 6, 1020, by + brh - 6], 18, fill=C["card_hi"])
        d.rounded_rectangle([82, by + brh / 2 - 7, 96, by + brh / 2 + 7], 4, fill=C["gold"] if on else C["line"])
        rich(d, 120, by + brh / 2, parts, on=on)


def slide_macro(d, rep, sl, hi):
    y = 360
    for title, gid, rows in sl["groups"]:
        bold(d, (60, y + 18), title, F(34), C["gold"], "lm", 1); y += 46
        for i, row in enumerate(rows):
            on = f"{gid}{i}" in hi
            if gid == "cal":
                h = 60
                d.rounded_rectangle([60, y, 1020, y + h], 16, fill=C["card_hi"] if on else C["card"],
                                    outline=C["gold"] if on else None, width=3 if on else 0)
                bold(d, (88, y + h / 2), row[0], F(28), C["gold"], "lm", 1 if on else 0)
                d.text((270, y + h / 2), row[1], font=F(30), fill=C["text"] if on else C["dim"], anchor="lm")
            else:
                h = 80
                d.rounded_rectangle([60, y, 1020, y + h], 18, fill=C["card_hi"] if on else C["card"],
                                    outline=C["gold"] if on else None, width=3 if on else 0)
                bold(d, (88, y + 28), row[0], F(30), C["text"], "lm", 1 if on else 0)
                d.text((88, y + 60), row[2], font=F(24), fill=C["sub"], anchor="lm")
                bold(d, (992, y + h / 2), row[1], F(40), C["gold"] if on else C["text"], "rm", 1)
            y += h + 8
        y += 4


def slide_sentiment(d, rep, sl, hi):
    title = sl.get("title", "市场情绪温度计")
    bold(d, (60, 334), title, F(34), C["text"], "lm", 1)
    d.text((60 + d.textlength(title, font=F(34)) + 14, 336), sl.get("subtitle", "霍华德·马克斯四层框架"),
           font=F(26), fill=C["sub"], anchor="lm")
    panel(d, [60, 370, 1020, 500], "banner" in hi)
    bold(d, (92, 414), sl["verdict"][0], F(56), C["gold"], "lm", 2)
    d.text((94, 466), sl["verdict"][1], font=F(30), fill=C["text"], anchor="lm")
    x = 1004 - 4 * 100 + 8
    for k in ("hot", "warm", "neutral", "cool"):
        label, col = ST[k]
        d.rounded_rectangle([x, 384, x + 92, 486], 16, fill=col)
        bold(d, (x + 46, 422), str(sl["counts"][k]), F(44), "#FFFFFF", "mm", 1)
        d.text((x + 46, 466), label, font=F(24), fill="#FFFFFF", anchor="mm")
        x += 100
    for ci, (ctitle, gid, items) in enumerate(sl["cols"]):
        x0 = 60 if ci == 0 else 550; x1 = x0 + 470
        bold(d, (x0, 540), ctitle, F(34), C["text"], "lm", 1)
        for i, (name, val, st) in enumerate(items):
            y = 572 + i * 78; on = f"{gid}{i}" in hi
            d.rounded_rectangle([x0, y, x1, y + 70], 16, fill=C["card_hi"] if on else C["card"],
                                outline=C["gold"] if on else None, width=3 if on else 0)
            d.text((x0 + 18, y + 35), name, font=F(25), fill=C["text"] if on else C["dim"], anchor="lm")
            bold(d, (x1 - 104, y + 35), val, F(29), C["text"], "rm", 1)
            label, col = ST[st]
            d.rounded_rectangle([x1 - 90, y + 15, x1 - 14, y + 55], 12, fill=col)
            d.text((x1 - 52, y + 35), label, font=F(23), fill="#FFFFFF", anchor="mm")


def slide_outlook(d, rep, sl, hi):
    b = sl["banner"]
    panel(d, [60, 360, 1020, 486], "banner" in hi)
    d.text((92, 392), b.get("label", "今日盘面"), font=F(28), fill=C["sub"], anchor="lm")
    bold(d, (92, 444), b["headline"], F(54), C["gold"], "lm", 2)
    for i, (t, col) in enumerate(b.get("stats", [])[:3]):
        bold(d, (992, 392 + i * 36), t, F(28), C[col] if col else C["text"], "rm", 0)
    y = 506
    for mkt, gid, tag, lines in sl["cards"]:
        scen = sl.get("scen", []) if gid == sl.get("scen_card", "us") else []
        h = 92 + len(lines) * 52 + (len(scen) * 80 + 12 if scen else 0); on = gid in hi
        panel(d, [60, y, 1020, y + h], on)
        bold(d, (92, y + 46), mkt, F(44), C["gold"], "lm", 2)
        tx = 92 + d.textlength(mkt, font=F(44)) + 22; tw = d.textlength(tag, font=F(30))
        d.rounded_rectangle([tx, y + 24, tx + tw + 36, y + 68], 22, outline=C["gold"], width=3)
        d.text((tx + 18 + tw / 2, y + 46), tag, font=F(30), fill=C["gold"], anchor="mm")
        for j, ln in enumerate(lines):
            ly = y + 108 + j * 52
            d.rounded_rectangle([96, ly - 6, 108, ly + 6], 4, fill=C["gold"] if on else C["line"])
            d.text((128, ly), ln, font=F(32), fill=C["text"] if on else C["dim"], anchor="lm")
        for k, (cond, res, dirn) in enumerate(scen):
            sy = y + 92 + len(lines) * 52 + 10 + k * 80; son = "scen" in hi; col = C[dirn]
            d.rounded_rectangle([92, sy, 988, sy + 68], 16, fill="#0F1A2E", outline=col if son else C["line"], width=3)
            tri(d, 124, sy + 34, 22, UP if dirn == "up" else DOWN, col)
            bold(d, (150, sy + 34), cond, F(30), C["text"], "lm", 1 if son else 0)
            d.text((960, sy + 34), res, font=F(30), fill=col, anchor="rm")
        y += h + 18


SLIDES = dict(intro=slide_intro, market=slide_market, macro=slide_macro, sentiment=slide_sentiment, outlook=slide_outlook)


def frame(bg, rep, tab_names, item):
    sl = rep["slides"][item["slide"]]; sent = sl["sentences"][item["idx"]]; hi = set(sent.get("hi", []))
    img = bg.copy().convert("RGBA"); ov = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(ov)
    if sl["type"] != "intro":
        header(d, rep); tabs(d, tab_names, tab_names.index(sl["tab"]))
        if sl.get("asof"):
            asof_badge(d, sl["asof"])
    SLIDES[sl["type"]](d, rep, sl, hi)
    subtitle(d, sent["sub"])
    footer(d, sl.get("src", rep.get("default_src", "数据来源：公开报道")))
    return Image.alpha_composite(img, ov).convert("RGB")


def main():
    rdir = sys.argv[1]; build = os.path.join(rdir, "build")
    rep = json.load(open(os.path.join(rdir, "report.json"), encoding="utf8"))
    tl = json.load(open(os.path.join(build, "timeline.json"), encoding="utf8"))
    jieba.setLogLevel(60)
    tab_names = [s["tab"] for s in rep["slides"] if s["type"] != "intro"]
    fdir = os.path.join(build, "frames"); os.makedirs(fdir, exist_ok=True)
    for f in os.listdir(fdir):
        os.remove(os.path.join(fdir, f))
    bg = background(); lines = []; sheet_frames = {}
    for k, it in enumerate(tl["items"]):
        p = os.path.join(fdir, f"f{k:03d}.png"); frame(bg, rep, tab_names, it).save(p)
        start = 0 if k == 0 else it["start"]
        lines += [f"file '{os.path.abspath(p)}'", f"duration {it['show_end'] - start:.3f}"]
        if it["idx"] == min(1, len(rep["slides"][it["slide"]]["sentences"]) - 1):
            sheet_frames[it["slide"]] = p
    lines.append(f"file '{os.path.abspath(p)}'")
    open(os.path.join(build, "frames.txt"), "w").write("\n".join(lines) + "\n")
    # 检查用拼图：每页取一帧
    ims = [Image.open(sheet_frames[i]).resize((360, 640)) for i in sorted(sheet_frames)]
    sheet = Image.new("RGB", (len(ims) * 370, 640), "white")
    for i, im in enumerate(ims):
        sheet.paste(im, (i * 370, 0))
    sheet.save(os.path.join(build, "contact_sheet.png"))
    print(f"frames: {len(tl['items'])}  total: {tl['total']:.1f}s  contact sheet: build/contact_sheet.png")


if __name__ == "__main__":
    main()
