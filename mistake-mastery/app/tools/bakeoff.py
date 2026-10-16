"""第 0 步试水：用孩子的真实卷子比较各家去手写效果，并检查识别切题和各接口连通性。

用法（在 mistake-mastery 目录下）：
    uv run python -m app.tools.bakeoff --check                       # 只测连通性：大模型、擦除接口、GitHub
    uv run python -m app.tools.bakeoff 卷子1.jpg 卷子2.jpg            # 各家擦除对比 + 识别切题
    uv run python -m app.tools.bakeoff --erasers baidu,youdao *.jpg   # 只比较指定的几家

结果写到 bakeoff-out/ 目录（不在任何 git 仓库里），用浏览器打开 bakeoff-out/index.html 并排对比。
这些卷子照片是孩子的数据，看完后可以删掉 bakeoff-out/。
"""

import argparse
import html
import json
import subprocess
import time
from pathlib import Path

import cv2
import numpy as np

from app.adapters import imaging
from app.adapters.eraser import make_eraser
from app.adapters.llm import PRESET_KEYS, LLMClient, resolve_preset
from app.config import Settings, get_settings, unknown_env_names
from app.db import Database
from app.services import prompts
from app.services.questions import bbox_to_pixels

ALL_ERASERS = ["local_color", "baidu", "youdao", "textin"]


def key_report(settings: Settings) -> tuple[list[str], bool]:
    """大模型密钥和默认模型的说明（不显示密钥，只显示开头 3 个字符），以及有没有可用的密钥。"""
    filled = {p: getattr(settings, attr).strip() for p, (attr, _, _) in PRESET_KEYS.items()}
    lines = ["  密钥：" + " · ".join(f"{name} {'已填（' + filled[p][:3] + '…）' if filled[p] else '未填'}"
                                  for p, (_, _, name) in PRESET_KEYS.items())]
    preset, why = resolve_preset(settings)
    lines.append(f"  各任务默认用 {preset}（{why}）")
    for name in unknown_env_names():
        lines.append(f"  ⚠ .env 里的 {name} 程序不认识（名字拼错了，或者少了 XT_ 前缀），这一行不起作用")
    if not any(filled.values()):
        lines.append("  ✗ 还没有大模型密钥：在 .env 里填 " + " 或 ".join(f"{env}（{name}）" for _, env, name
                                                             in PRESET_KEYS.values()) + "，保存后再运行")
        return lines, False
    if not filled[preset]:
        other = next(p for p in PRESET_KEYS if filled[p])
        lines.append(f"  ⚠ 用的是 {preset}，但没填它的密钥 {PRESET_KEYS[preset][1]}，填了的是 {PRESET_KEYS[other][1]}："
                     f"把 .env 里的 XT_MODEL_PRESET 改成 {other}，或者删掉这一行（自动选）")
    return lines, True


def check(settings: Settings) -> None:
    print("== 大模型 ==")
    lines, usable = key_report(settings)
    print("\n".join(lines))
    if usable:
        check_models(settings)
    check_services(settings)


def check_models(settings: Settings) -> None:
    db = Database(Path(".bakeoff-tmp.db"))
    llm = LLMClient(settings, db, Path("bakeoff-out/.cache"))
    # 要看图的任务发一张小图（白底黑方块），确认这个模型真的能看图
    square = np.full((120, 160, 3), 255, np.uint8)
    square[30:90, 50:110] = 0
    image_url, _ = imaging.data_url_jpeg(square)
    see = [{"type": "image_url", "image_url": {"url": image_url}},
           {"type": "text", "text": '图片中间有没有一个黑色方块？只输出 JSON：{"ok": true, "black_square": true 或 false}'}]
    for task, needs_image in (("recognize", True), ("bank", True), ("solve", True), ("classify", False),
                              ("lesson", False)):
        content = see if needs_image else '只输出 JSON：{"ok": true}'
        try:
            out = llm.chat_json(task, [{"role": "user", "content": content}], prompt_version=f"check-{time.time()}")
            note = "（看图）" if needs_image else ""
            bad = needs_image and not (isinstance(out, dict) and out.get("black_square") is True)
            print(f"  {task:10s} {llm.models[task]:30s} {'⚠ 没认出图里的方块，可能不支持看图' if bad else '✓'}{note} {out}")
        except Exception as exc:  # noqa: BLE001
            print(f"  {task:10s} {llm.models[task]:30s} ✗ {exc}")
    db.dispose()
    Path(".bakeoff-tmp.db").unlink(missing_ok=True)


def check_services(settings: Settings) -> None:
    print("== 去手写接口（用一张空白小图测连通性）==")
    blank = imaging.encode_jpeg(np.full((200, 300, 3), 255, np.uint8))
    for name in ALL_ERASERS[1:]:
        try:
            make_eraser(settings, name).erase(blank)
            print(f"  {name:8s} ✓")
        except Exception as exc:  # noqa: BLE001
            print(f"  {name:8s} ✗ {exc}")

    print("== GitHub 数据仓库 ==")
    data = settings.data_dir
    if not (data / ".git").exists():
        print(f"  ✗ {data} 不是 git 仓库：先 git clone 你的私有数据仓库，并在 .env 里设置 XT_DATA_DIR")
        return
    r = subprocess.run(["git", "-C", str(data), "ls-remote", "--heads", "origin"], capture_output=True, text=True,
                       timeout=60)
    print("  ✓ 可以连上远端" if r.returncode == 0 else f"  ✗ 连不上远端：{r.stderr.strip()[-300:]}")


def bakeoff(settings, files: list[Path], erasers: list[str], recognize: bool, subject: str) -> None:  # noqa: ANN001
    out = Path("bakeoff-out")
    out.mkdir(exist_ok=True)
    rows = []
    llm = None
    db = None
    if recognize:
        db = Database(out / ".bakeoff.db")
        llm = LLMClient(settings, db, out / ".cache")
    for f in files:
        print(f"== {f.name} ==")
        jpeg, _, _ = imaging.normalize_upload(f.read_bytes())
        img = imaging.decode(jpeg)
        t = imaging.detect_page_transform(img)
        corrected = imaging.apply_transform(img, t)
        stem = f.stem
        cv2.imwrite(str(out / f"{stem}-0-corrected.jpg"), corrected)
        cells = [(f"矫正后（{'已矫正' if t else '未检测到纸张边缘'}）", f"{stem}-0-corrected.jpg", "")]
        for name in erasers:
            t0 = time.monotonic()
            try:
                data = imaging.encode_png(corrected) if name == "local_color" else imaging.encode_jpeg(corrected, 92)
                res = imaging.decode(make_eraser(settings, name).erase(data))
                path = f"{stem}-{name}.png"
                cv2.imwrite(str(out / path), res)
                note = f"{time.monotonic() - t0:.1f} 秒"
            except Exception as exc:  # noqa: BLE001
                path, note = "", f"失败：{exc}"
            print(f"  擦除 {name:12s} {note}")
            cells.append((name, path, note))
        if llm is not None:
            try:
                url, _ = imaging.data_url_jpeg(corrected)
                rec = llm.chat_json("recognize", prompts.recognize_messages(subject, url, "page"),
                                    prompt_version=prompts.RECOGNIZE_VERSION)
                h, w = corrected.shape[:2]
                overlay = corrected.copy()
                for q in rec.get("questions", []):
                    x0, y0, x1, y1 = (int(v) for v in bbox_to_pixels(q.get("bbox"), w, h))
                    cv2.rectangle(overlay, (x0, y0), (x1, y1), (0, 140, 255), 4)
                    cv2.putText(overlay, str(q.get("number_label", "?")), (x0 + 8, y0 + 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 140, 255), 3)
                cv2.imwrite(str(out / f"{stem}-recognize.jpg"), overlay)
                (out / f"{stem}-recognize.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2),
                                                            encoding="utf-8")
                cells.append(("识别切题（橙色框）", f"{stem}-recognize.jpg", f"{len(rec.get('questions', []))} 道题"))
                print(f"  识别 {len(rec.get('questions', []))} 道题")
            except Exception as exc:  # noqa: BLE001
                cells.append(("识别切题", "", f"失败：{exc}"))
                print(f"  识别失败：{exc}")
        rows.append((f.name, cells))
    if db:
        db.dispose()

    parts = ["<!doctype html><meta charset=utf-8><title>擦除对比</title><style>"
             "body{font-family:sans-serif;margin:16px}table{border-collapse:collapse}td{vertical-align:top;"
             "padding:6px;border:1px solid #ddd}img{width:420px}</style>"
             "<h1>去手写对比</h1><p>重点看：几何图上的辅助线、红笔批改、浅色铅笔、和印刷字重叠的笔迹。</p>"]
    for name, cells in rows:
        parts.append(f"<h2>{html.escape(name)}</h2><table><tr>")
        for title, path, note in cells:
            img = f"<a href='{path}' target=_blank><img src='{path}'></a>" if path else ""
            parts.append(f"<td><b>{html.escape(title)}</b><br><small>{html.escape(note)}</small><br>{img}</td>")
        parts.append("</tr></table>")
    (out / "index.html").write_text("".join(parts), encoding="utf-8")
    print(f"\n完成：用浏览器打开 {out.resolve() / 'index.html'}")


def main() -> None:
    p = argparse.ArgumentParser(description="第 0 步试水：擦除对比、识别切题、连通性检查")
    p.add_argument("files", nargs="*", type=Path, help="卷子照片")
    p.add_argument("--check", action="store_true", help="只检查各接口和 GitHub 的连通性")
    p.add_argument("--erasers", default=",".join(ALL_ERASERS), help="要比较的擦除接口，逗号分隔")
    p.add_argument("--no-recognize", action="store_true", help="不跑识别切题（省一点模型费用）")
    p.add_argument("--subject", default="math", choices=["math", "physics"])
    args = p.parse_args()
    settings = get_settings()
    if args.check or not args.files:
        check(settings)
        return
    bakeoff(settings, args.files, [e for e in args.erasers.split(",") if e], not args.no_recognize, args.subject)


if __name__ == "__main__":
    main()
