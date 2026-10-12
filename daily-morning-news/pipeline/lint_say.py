"""朗读文本检查：找出 TTS 容易读错的地方。

用法: python3 lint_say.py <report.json> <models_dir> [--strict]
检查项：
  1. 替换后仍残留的英文字母/阿拉伯数字（引擎会丢弃字母，数字读法不可控）——应写成汉字
  2. 单独成词的多音字（如"为""处""只"），会按词典默认读音读——应换说法或加到 lexicon_extra
  3. 未登录词里含多音字，会逐字按默认读音读——逐个确认，读错的加到 lexicon_extra
"""
import json
import os
import re
import sys

import jieba

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from synth import load_extra_lexicon, prepare_say  # noqa: E402

POLY = set("为处只长行重调还得地着了都便传种相乐发干降几差曾应藏将朝露解角会率省塞宁曲区转觉没似参称冲当")
SAFE_SINGLE = set("了都和的得地着将")  # 默认读音在财经语境下通常正确，不单独报错


def main():
    path, models = sys.argv[1], sys.argv[2]; strict = "--strict" in sys.argv
    z = os.path.join(models, "matcha-icefall-zh-baker")
    rep = json.load(open(path, encoding="utf8"))
    lex = {}
    for line in load_extra_lexicon(rep) + list(open(os.path.join(z, "lexicon.txt"), encoding="utf8")):
        p = line.split()
        if p and p[0] not in lex:
            lex[p[0]] = " ".join(p[1:])
    jieba.setLogLevel(60); jieba.set_dictionary(os.path.join(z, "dict", "jieba.dict.utf8"))
    problems, notes = [], []
    for si, sl in enumerate(rep["slides"]):
        for j, s in enumerate(sl["sentences"]):
            say = prepare_say(s["say"]); where = f"[{sl.get('tab', sl['type'])} #{j}]"
            if re.search(r"[A-Za-z0-9]", say):
                problems.append(f"{where} 含字母/数字（请写成汉字）：{say}")
            for w in jieba.cut(say):
                w = w.strip()
                if not w or not re.match(r"[一-鿿]+$", w):
                    continue
                if w in lex and len(w) > 1:
                    continue
                if len(w) == 1 and w in POLY and w not in SAFE_SINGLE:
                    problems.append(f"{where} 单独的多音字「{w}」按 {lex.get(w, '?')} 读：{say}")
                elif len(w) > 1 and any(c in POLY for c in w):
                    notes.append(f"{where} 未登录词「{w}」逐字读作 " + " ".join(lex.get(c, "?") for c in w))
    problems = list(dict.fromkeys(problems))
    for p in problems:
        print("✗", p)
    for n in sorted(set(notes)):
        print("·", n)
    print(f"{len(problems)} 个问题，{len(set(notes))} 条需确认")
    sys.exit(1 if strict and problems else 0)


if __name__ == "__main__":
    main()
