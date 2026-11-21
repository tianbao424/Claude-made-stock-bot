#!/usr/bin/env python3
"""report.json 发布前自查：字幕长度、画面文字长度、数据时点五处是否齐全、句数。
用法: python3 check_report.py <report_dir>     有 ✗ 时退出码为 1"""
import json, os, sys

d = sys.argv[1]
r = json.load(open(os.path.join(d, "report.json"), encoding="utf8"))
bad, warn = [], []
sl = {s.get("tab", "intro"): s for s in r["slides"]}

n = 0
for s in r["slides"]:
    for i, x in enumerate(s["sentences"]):
        n += 1
        if len(x["sub"]) > 45:
            bad.append(f"[{s.get('tab', 'intro')} #{i}] 字幕 {len(x['sub'])} 字 > 45，拆句：{x['sub']}")
        if any(c.isascii() and c.isalpha() for c in x["say"].replace("AI", "").replace("A股", "")):
            bad.append(f"[{s.get('tab', 'intro')} #{i}] say 含英文字母：{x['say']}")
width = lambda t: sum(0.45 if c.isascii() else 1 for c in t)   # 英文字母不到半个汉字宽
for s in r["slides"]:
    src = s.get("src", r.get("default_src", ""))
    if width(src) > 35:   # 实测 36 个汉字宽会被截断；英文多的长来源行显示正常
        bad.append(f"[{s.get('tab', 'intro')}] 页脚来源约 {width(src):.0f} 字宽 > 35，会被截断：{src}")
if not 18 <= n <= 28:
    warn.append(f"共 {n} 句，3 分钟版建议 22–25 句")

# 数据时点
dn = dict(r.get("data_note", []))
if not dn.get("美股") or not dn.get("A股 · 港股"):
    bad.append("data_note 缺美股或「A股 · 港股」")
intro = sl["intro"]["sentences"]
if not any("数据时点" in x["sub"] and "note" in x["hi"] for x in intro):
    bad.append("开场缺数据时点句（hi 需含 note）")
for tab, key in (("美股", "美股方面"), ("A股", "A股方面"), ("港股", "港股方面")):
    s = sl.get(tab)
    if not s:
        bad.append(f"缺 {tab} 页"); continue
    if not s.get("asof"):
        bad.append(f"{tab} 页缺 asof")
    if not s["sentences"][0]["sub"].startswith(key):
        bad.append(f"{tab} 页第一句应以「{key}」开头")
md = os.path.join(d, "script.md")
if os.path.exists(md) and "数据时点" not in open(md, encoding="utf8").read()[:400]:
    bad.append("script.md 开头缺「数据时点」")
if sl["展望"]["sentences"][-1]["sub"] != "祝您账户常红，天天开心！":
    bad.append("结尾应为「祝您账户常红，天天开心！」")

for m in bad: print("✗", m)
for m in warn: print("·", m)
print(f"{len(bad)} 个问题，{len(warn)} 条提示")
sys.exit(1 if bad else 0)
