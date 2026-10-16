"""题库：把真题、各区一模二模、区统考的卷子（PDF 或照片）切成一道道带官方答案的题；录入错题时自动匹配。

导入流程（见 docs/10-question-bank.md）：
上传原卷和答案 → 拆页、渲染、取 PDF 文字层 → 逐页识别（试题页切题，答案页按题号取答案；
跨页的题合并）→ 按题号对上答案 → 分类知识点 → AI 独立解一遍，和官方答案对不上的标出来
→ 已经录入的错题如果在这套卷子里，补上官方答案。
"""

import logging
import re
import shutil
import threading
import unicodedata
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from app.adapters import imaging, pdf
from app.adapters.llm import CostCapExceeded, LLMError
from app.ids import now_iso
from app.jobs import JobHandle
from app.models import BankItem, BankPaper, Mistake, Question, QuestionKp
from app.services import prompts
from app.services.questions import VALID_TYPES, apply_classification, content_hash

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.context import AppContext

log = logging.getLogger(__name__)

EXAM_KINDS = {"zhongkao": "中考", "yimo": "一模", "ermo": "二模", "midterm": "期中", "final": "期末",
              "monthly": "月考", "other": "其他"}
MAX_FILE_BYTES = 60 * 1024 * 1024
MAX_PAGES = 60
CLASSIFY_BATCH = 12


# ---------------------------------------------------------------- 上传


def create_paper(ctx: "AppContext", *, subject: str, title: str, year: int | None, region: str | None,
                 exam_kind: str, paper_files: list[tuple[str, bytes]], answer_files: list[tuple[str, bytes]],
                 verify: bool = True) -> tuple[str, str]:
    """保存上传的文件，创建导入任务，返回 (paper_id, job_id)。"""
    if subject not in prompts.SUBJECT_NAMES:
        raise ValueError(f"不支持的学科：{subject}")
    if not paper_files:
        raise ValueError("请上传试卷的 PDF 或照片")
    with ctx.db.session() as s:
        paper = BankPaper(subject=subject, title=(title or "").strip()[:100], year=year, region=region or None,
                          exam_kind=exam_kind if exam_kind in EXAM_KINDS else "other", status="processing")
        s.add(paper)
        s.flush()
        files = []
        for role, items in (("paper", paper_files), ("answer", answer_files)):
            for i, (name, data) in enumerate(items, start=1):
                files.append(_save_file(ctx, paper.id, role, i, name, data))
        if sum(f["pages"] for f in files) > MAX_PAGES:
            raise ValueError(f"一次最多导入 {MAX_PAGES} 页")
        paper.files = files
        paper_id = paper.id
    return paper_id, ctx.jobs.submit("bank_import", {"paper_id": paper_id, "verify": verify})


def _save_file(ctx: "AppContext", paper_id: str, role: str, i: int, name: str, data: bytes) -> dict:
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"{name} 太大了（超过 60MB）")
    base = ctx.storage.bank_dir(paper_id)
    name = (name or "")[:100]
    if pdf.is_pdf(data):
        n = pdf.page_count(data)
        if n == 0:
            raise ValueError(f"{name} 里没有页面")
        return {"role": role, "kind": "pdf", "name": name, "pages": n,
                "path": ctx.storage.write(f"{base}/{role}-{i}.pdf", data)}
    try:
        jpeg, _w, _h = imaging.normalize_upload(data)
    except Exception as exc:  # noqa: BLE001 —— PIL 对各种坏文件抛的异常类型不一
        raise ValueError(f"{name} 既不是 PDF 也不是图片") from exc
    return {"role": role, "kind": "image", "name": name, "pages": 1,
            "path": ctx.storage.write(f"{base}/{role}-{i}.jpg", jpeg)}


# ---------------------------------------------------------------- 页面图片


def _cache_dir(ctx: "AppContext", paper_id: str):  # noqa: ANN202
    return ctx.storage.cache / "bank" / paper_id


def page_image(ctx: "AppContext", paper_id: str, files: list[dict], pg: dict) -> np.ndarray:
    """一页的图片：PDF 现渲染，照片做透视矫正；缓存在 .local/cache（不进 git）。"""
    cache = _cache_dir(ctx, paper_id) / f"p{pg['n']}.jpg"
    if cache.exists():
        return imaging.decode(cache.read_bytes())
    f = files[pg["file"]]
    data = ctx.storage.read(f["path"])
    if f["kind"] == "pdf":
        img = pdf.render_page(data, pg["index"])
    else:
        img = imaging.apply_transform(imaging.decode(data), pg.get("transform"))
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(imaging.encode_jpeg(img, 90))
    return img


def _page_text(ctx: "AppContext", files: list[dict], pg: dict) -> str:
    f = files[pg["file"]]
    return pdf.page_text(ctx.storage.read(f["path"]), pg["index"]) if f["kind"] == "pdf" else ""


def question_image(ctx: "AppContext", paper: BankPaper, regions: list[dict]) -> np.ndarray:
    """一道题的截图；跨页的题把几段竖着拼起来。"""
    pages = {p["n"]: p for p in paper.pages or []}
    crops = []
    for r in regions:
        pg = pages.get(r.get("page"))
        if pg is None:
            continue
        img = page_image(ctx, paper.id, paper.files, pg)
        h, w = img.shape[:2]
        x0, y0, x1, y1 = r["bbox"]
        crops.append(imaging.crop(img, [x0 / 1000 * w, y0 / 1000 * h, x1 / 1000 * w, y1 / 1000 * h], pad=0))
    if not crops:
        raise ValueError("这道题没有位置信息")
    width = max(c.shape[1] for c in crops)
    padded = [np.pad(c, ((0, 0), (0, width - c.shape[1]), (0, 0)), constant_values=255) for c in crops]
    return np.vstack(padded)


# ---------------------------------------------------------------- 导入任务


def _split_pages(ctx: "AppContext", files: list[dict]) -> list[dict]:
    pages: list[dict] = []
    for fi, f in enumerate(files):
        if f["kind"] == "pdf":
            for idx in range(pdf.page_count(ctx.storage.read(f["path"]))):
                pages.append({"n": len(pages) + 1, "file": fi, "index": idx, "role": f["role"]})
        else:
            img = imaging.decode(ctx.storage.read(f["path"]))
            pages.append({"n": len(pages) + 1, "file": fi, "index": 0, "role": f["role"],
                          "transform": imaging.detect_page_transform(img)})
    return pages


def _segments(img: np.ndarray) -> list[tuple[float, float, str]]:
    """横版（A3 双栏）的页面分成左右两半分别识别，小字认得更准。"""
    h, w = img.shape[:2]
    if w > h * 1.15:
        return [(0.0, 0.5, "一页（A3 横版卷的左半页）"), (0.5, 1.0, "一页（A3 横版卷的右半页）")]
    return [(0.0, 1.0, "一页")]


def _seg_bbox(bbox: object, x0: float, x1: float, seg_w: int, seg_h: int) -> list[float]:
    """模型在半页上给的坐标，换算成整页的 0–1000 归一化坐标。"""
    try:
        b = [float(v) for v in bbox]  # type: ignore[union-attr]
        if len(b) != 4:
            raise ValueError
    except (TypeError, ValueError):
        b = [0.0, 0.0, 1000.0, 1000.0]
    if max(b) > 1000:  # 有的模型给像素坐标
        b = [b[0] / seg_w * 1000, b[1] / seg_h * 1000, b[2] / seg_w * 1000, b[3] / seg_h * 1000]
    bx0, bx1 = sorted(min(1000.0, max(0.0, v)) for v in (b[0], b[2]))
    by0, by1 = sorted(min(1000.0, max(0.0, v)) for v in (b[1], b[3]))
    if bx1 - bx0 < 5 or by1 - by0 < 5:
        bx0, by0, bx1, by1 = 0.0, 0.0, 1000.0, 1000.0
    span = x1 - x0
    return [round((x0 + bx0 / 1000 * span) * 1000, 1), round(by0, 1),
            round((x0 + bx1 / 1000 * span) * 1000, 1), round(by1, 1)]


def norm_label(label: object) -> str | None:
    """题号规范化：取第一个整数（"27."、"第27题"、"27(1)" 都是 27）。"""
    m = re.search(r"\d+", unicodedata.normalize("NFKC", str(label or "")))
    return str(int(m.group())) if m else None


def _new_question(item: dict, region: dict) -> dict:
    qtype = item.get("question_type")
    return {
        "number_label": str(item.get("number_label") or "").strip()[:20],
        "type": qtype if qtype in VALID_TYPES else "solve",
        "stem_md": item.get("stem_md") or "",
        "options": item.get("options") or None,
        "sub_questions": item.get("sub_questions") or None,
        "has_figure": bool(item.get("has_figure")),
        "points": (str(item.get("points")).strip()[:20] if item.get("points") else None),
        "answer_shown": bool(item.get("answer_shown")),
        "regions": [region],
    }


_SENTENCE_END = set("。？！：；….?!:;）)】」”\"")
_NEW_PART = re.compile(r"^\s*(?:[（(]\s*\d+\s*[）)]|[①-⑳]|[A-D]\s*[．.、]|\d+\s*[．.、])")  # 小问、选项开头的另起一段
# 模型有时给只有图的后半段写一句说明，比如"（接上一页第 9 题的图：……）"，那不是卷面上的字
_DESCRIBED = re.compile(r"^[（(][^（）()]*(?:接上|上一页|续)[^（）()]*[）)]$")


def _extend(last: dict, item: dict, region: dict | None) -> None:
    """跨页（或跨半页）的题：把后半段接到上一道题上（region 为 None 时只合并文字）。"""
    if region is not None:
        last["regions"].append(region)
    last["answer_shown"] = last.get("answer_shown") or bool(item.get("answer_shown"))
    stem = (item.get("stem_md") or "").strip()
    if stem and stem not in last["stem_md"] and not _DESCRIBED.match(stem):
        # 上一页最后一句没说完（"……用电压表测得 R1 两" + "端的电压……"）就直接接上，否则另起一段
        mid = last["stem_md"] and last["stem_md"][-1] not in _SENTENCE_END and not _NEW_PART.match(stem)
        sep = "" if mid else "\n\n"
        last["stem_md"] = (last["stem_md"] + sep + stem).strip()
    if item.get("options"):
        keys = {o.get("key") for o in last.get("options") or [] if isinstance(o, dict)}
        last["options"] = (last.get("options") or []) + [o for o in item["options"]
                                                           if isinstance(o, dict) and o.get("key") not in keys]
    if item.get("sub_questions"):
        last["sub_questions"] = (last["sub_questions"] or []) + list(item["sub_questions"])
    last["has_figure"] = last["has_figure"] or bool(item.get("has_figure"))


def _add_material(materials: list[dict], label: str | None, item: dict, region: dict | None) -> None:
    """模型列出的阅读材料：文字总是收下；范围只在没有文字层（扫描件、照片）时用模型给的框。"""
    if label is None:
        return
    cur = next((mt for mt in reversed(materials) if label in mt["labels"]), None)
    if cur is None:
        cur = {"labels": [label], "regions": [], "text": ""}
        materials.append(cur)
    stem = (item.get("stem_md") or "").strip()
    if stem and stem not in cur["text"]:
        cur["text"] = (cur["text"] + "\n\n" + stem).strip()
    if region is not None:
        cur["regions"].append(region)


def _take_material(materials: list[dict], q: dict, label: str | None) -> list[dict]:
    """把属于这道题的阅读材料放到题目最前面；返回还没用上的材料。"""
    if label is None:
        return materials
    for mt in materials:
        if label in mt["labels"]:
            q["regions"][:0] = mt["regions"]
            if mt["text"]:
                q["stem_md"] = (mt["text"] + "\n\n" + q["stem_md"]).strip()
    # 一段材料对应几道题时，最后一道题用完再丢
    return [mt for mt in materials if label not in mt["labels"] or label != mt["labels"][-1]]


def _merge_answer(answers: dict[str, dict], item: dict) -> None:
    label = norm_label(item.get("number_label"))
    if not label:
        return
    final = str(item.get("final_answer") or "").strip()
    sol = (item.get("solution_md") or "").strip()
    cur = answers.setdefault(label, {"final": "", "solution": ""})
    if final and final not in cur["final"]:
        cur["final"] = f"{cur['final']}；{final}" if cur["final"] else final
    if sol and sol not in cur["solution"]:
        cur["solution"] = f"{cur['solution']}\n\n{sol}" if cur["solution"] else sol


# ---------------------------------------------------------------- 用 PDF 文字层校准题目范围
#
# Word / WPS 导出的卷子有文字层，每行的位置是准的。模型给的框只当提示：
# 题目从"27．"这一行开始，到下一个边界（下一题、【答案】【解答】、大题标题）为止。
# 答案版卷子（每题后面紧跟【答案】）这样截出来的图里就不会带上答案。
# 科普阅读题的短文在题号前面（"请阅读《……》并回答第 24 题"），可能跨页：从这一行到"24．"之间的内容放到第 24 题最前面。

_Q_START = re.compile(r"^\s*(\d{1,3})\s*[．.、](?!\d)")
_ANS_MARK = re.compile(r"^\s*[【\[]\s*(答案|分析|解答|详解|解析|点评|点睛|考点|专题|分值|难度)")
_SECTION = re.compile(r"^\s*[一二三四五六七八九十]+\s*[、．.]?\s*\S{0,8}?题")
# 只认写明了题号的说明行；题目里面的"阅读下面的材料……"不算
_MATERIAL = re.compile(r"^\s*请?(?:认真)?阅读.{0,40}?(?:回答|完成|解答|作答)\D{0,6}?(\d{1,3})\s*"
                       r"(?:[-~～—–至到、]\s*第?\s*(\d{1,3}))?\s*小?题")
_FOOTER = re.compile(r"^\s*第\s*\d+\s*页")
_POINTS = re.compile(r"[（(]\s*(\d+)\s*分\s*[)）]")
PAD = 6  # 0–1000 坐标，约 2 毫米


@dataclass
class _Seg:
    lines: list  # list[pdf.Line]，按从上到下排好
    images: list  # [(x0, y0, x1, y1)]
    lo: float
    hi: float


@dataclass
class _Anchor:
    bbox: list[float]
    closed_by: str  # answer（下面是答案）| question（下一题）| section（大题标题）| page_end（接到下一页）
    points: str | None = None


def _layouts(ctx: "AppContext", files: list[dict], pages: list[dict]) -> dict[int, "pdf.Layout"]:
    """每页的文字层版面；去掉每页都在同一位置出现的页眉页脚（学校名、网站水印、页码）。"""
    out: dict[int, pdf.Layout] = {}
    data: dict[int, bytes] = {}
    for pg in pages:
        f = files[pg["file"]]
        if f["kind"] == "pdf":
            raw = data.setdefault(pg["file"], ctx.storage.read(f["path"]))
            out[pg["n"]] = pdf.page_layout(raw, pg["index"])
    key = lambda ln: re.sub(r"\d+", "#", ln.text)  # noqa: E731 —— 页码不同也算同一行
    counts = Counter(key(ln) for lay in out.values() for ln in lay.lines if ln.y1 < 80 or ln.y0 > 920)
    running = {k for k, n in counts.items() if len(out) >= 3 and n >= max(3, len(out) // 2)}
    for lay in out.values():
        lay.lines = [ln for ln in lay.lines if not _FOOTER.match(ln.text)
                     and not ((ln.y1 < 80 or ln.y0 > 920) and key(ln) in running)]
    return out


def _seg(layout: "pdf.Layout | None", x0: float, x1: float) -> _Seg | None:
    if layout is None or not layout.lines:
        return None
    lo, hi = x0 * 1000, x1 * 1000
    return _Seg([ln for ln in layout.lines if lo <= (ln.x0 + ln.x1) / 2 <= hi],
                [im for im in layout.images if lo <= (im[0] + im[2]) / 2 <= hi], lo, hi)


def _boundary(text: str) -> str | None:
    if _ANS_MARK.match(text):
        return "answer"
    if _Q_START.match(text):
        return "question"
    if _MATERIAL.match(text):
        return "material"
    if _SECTION.match(text):
        return "section"
    return None


def _region(seg: _Seg, top: float) -> _Anchor | None:
    """从 top 往下，到下一个边界为止的范围。"""
    end, closed = None, "page_end"
    for ln in seg.lines:
        if ln.y0 > top + 1 and _boundary(ln.text):
            end, closed = ln.y0, _boundary(ln.text)
            break
    boxes = [(ln.x0, ln.y0, ln.x1, ln.y1) for ln in seg.lines if ln.y0 >= top - 1 and (end is None or ln.y0 < end)]
    boxes += [im for im in seg.images if (im[1] + im[3]) / 2 >= top and (end is None or (im[1] + im[3]) / 2 < end)]
    if not boxes:
        return None
    bottom = end - 5 if end is not None else max(b[3] for b in boxes) + PAD  # 留出 2 毫米，别切到下一行的字
    return _Anchor([round(max(seg.lo, min(b[0] for b in boxes) - PAD), 1), round(max(0.0, top - PAD), 1),
                    round(min(seg.hi, max(b[2] for b in boxes) + PAD), 1), round(min(1000.0, bottom), 1)], closed)


def _anchor_question(seg: _Seg, label: object, hint_y: float) -> _Anchor | None:
    """题号为 label 的那一行开始的范围；同一页有几行都像这个题号时，取离模型给的位置最近的。"""
    n = norm_label(label)
    if n is None:
        return None
    starts = [ln for ln in seg.lines if (m := _Q_START.match(ln.text)) and str(int(m.group(1))) == n]
    if not starts:
        return None
    start = min(starts, key=lambda ln: abs(ln.y0 - hint_y))
    anchor = _region(seg, start.y0)
    if anchor is not None and (m := _POINTS.search(start.text)):
        anchor.points = f"{m.group(1)}分"
    return anchor


def _material_labels(m: re.Match) -> list[str]:
    a = int(m.group(1))
    b = int(m.group(2)) if m.group(2) else a
    return [str(n) for n in range(a, b + 1)] if a <= b <= a + 5 else [str(a)]


def _anchor_top(seg: _Seg) -> _Anchor | None:
    """页面最上面、第一个边界之前的内容（上一页那道题的后半段）。"""
    tops = [ln.y0 for ln in seg.lines] + [im[1] for im in seg.images]
    if not tops:
        return None
    top = min(tops)
    first = seg.lines[0] if seg.lines else None
    if first is not None and first.y0 <= top + 1 and _boundary(first.text):
        return None  # 这一页一开头就是新的题、答案或大题标题
    return _region(seg, top)


def import_paper(ctx: "AppContext", handle: JobHandle, payload: dict) -> dict:
    pid = payload["paper_id"]
    try:
        return _import(ctx, handle, pid, verify=payload.get("verify", True))
    except Exception as exc:
        with ctx.db.session() as s:
            paper = s.get(BankPaper, pid)
            if paper is not None:
                paper.status = "failed"
                paper.error = str(exc)[:1000]
        raise


def _import(ctx: "AppContext", handle: JobHandle, pid: str, *, verify: bool) -> dict:
    with ctx.db.session() as s:
        paper = s.get(BankPaper, pid)
        if paper is None:
            return {"skipped": True}
        subject, files = paper.subject, list(paper.files)
        paper.status, paper.error = "processing", None
    shutil.rmtree(_cache_dir(ctx, pid), ignore_errors=True)

    handle.progress("拆分页面", 2)
    pages = _split_pages(ctx, files)
    with ctx.db.session() as s:
        s.get(BankPaper, pid).pages = pages

    layouts = _layouts(ctx, files, pages)
    questions: list[dict] = []
    answers: dict[str, dict] = {}
    errors: list[str] = []
    header = None
    # 上一道题最后一段是怎么结束的：answer = 后面已经是答案，下一页开头的内容只能是解答；
    # page_end = 题目接到了下一页；None = 没有文字层，只能信模型
    last_closed: str | None = None
    # 题号前面的阅读材料，等对应的题出现时放到它最前面：{"labels": [...], "regions": [...], "text": str}
    materials: list[dict] = []
    open_material: dict | None = None  # 接到了下一页的那段材料
    for i, pg in enumerate(pages):
        handle.progress(f"第 {i + 1}/{len(pages)} 页：识别", 5 + int(i / len(pages) * 55))
        img = page_image(ctx, pid, files, pg)
        text = _page_text(ctx, files, pg)
        has_q = has_a = False
        h, w = img.shape[:2]
        for x0, x1, part in _segments(img):
            seg_img = img[:, int(x0 * w):int(x1 * w)]
            seg = _seg(layouts.get(pg["n"]), x0, x1)
            url, _ = imaging.data_url_jpeg(seg_img)
            prev_label = questions[-1]["number_label"] if questions else None
            try:
                out = ctx.llm.chat_json("bank", prompts.bank_page_messages(
                    subject, url, text, pg["role"], part, prev_label), prompt_version=prompts.BANK_PAGE_VERSION) or {}
            except CostCapExceeded:
                raise
            except LLMError as exc:
                errors.append(f"第 {pg['n']} 页识别失败：{exc}")
                continue
            header = header or out.get("header")
            items = out.get("questions") or []
            # 阅读材料：有文字层时按"请阅读……回答第 N 题"这一行找；上一页的材料没完的话，这一页开头接着是材料
            text_material = top_is_material = False
            if seg is not None:
                if open_material is not None:
                    top = _anchor_top(seg)
                    if top is not None:
                        open_material["regions"].append({"page": pg["n"], "bbox": top.bbox})
                        text_material = top_is_material = True
                    open_material = open_material if top is not None and top.closed_by == "page_end" else None
                for ln in seg.lines:
                    if (m := _MATERIAL.match(ln.text)) and (r := _region(seg, ln.y0)) is not None:
                        mt = {"labels": _material_labels(m), "text": "", "regions": [{"page": pg["n"], "bbox": r.bbox}]}
                        materials.append(mt)
                        open_material, text_material = (mt if r.closed_by == "page_end" else None), True
            # 页面开头是不是上一题的后半段，以模型的判断为准（答案版卷子里那可能是答案的图）；
            # 范围按文字层算，上一题的答案已经开始了的话一律不算题目；开头接着是阅读材料的话也不算
            continued_done = top_is_material
            for item in items:
                model_bbox = _seg_bbox(item.get("bbox"), x0, x1, seg_img.shape[1], seg_img.shape[0])
                label = norm_label(item.get("number_label"))
                if item.get("material"):
                    _add_material(materials, label, item, None if text_material else
                                  {"page": pg["n"], "bbox": model_bbox})
                    continue
                same = bool(questions) and label is not None and label == norm_label(questions[-1]["number_label"])
                if questions and (item.get("continued") or same):
                    if top_is_material and item.get("continued"):
                        continue  # 模型把接着的阅读材料当成了上一题的后半段
                    region = None
                    if not continued_done and last_closed != "answer":  # 上一题的答案已经开始了：这是解答，不算题目
                        top = _anchor_top(seg) if seg is not None else None
                        region = {"page": pg["n"], "bbox": top.bbox if top else model_bbox}
                        last_closed, continued_done = (top.closed_by if top else None), True
                    _extend(questions[-1], item, region)
                    continue
                anchor = _anchor_question(seg, item.get("number_label"), model_bbox[1]) if seg is not None else None
                q = _new_question(item, {"page": pg["n"], "bbox": anchor.bbox if anchor else model_bbox})
                q["points"] = q["points"] or (anchor.points if anchor else None)
                materials = _take_material(materials, q, label)
                questions.append(q)
                last_closed = anchor.closed_by if anchor else None
                has_q = True
            for item in out.get("answers") or []:
                _merge_answer(answers, item)
                has_a = True
        pg["kind"] = "mixed" if has_q and has_a else "questions" if has_q else "answers" if has_a else "other"

    if not questions:
        raise RuntimeError("；".join(errors) or "没有识别出题目。请确认上传的是试卷（不是只有答案）")

    handle.progress("保存题目", 60)
    with ctx.db.session() as s:
        _delete_items(s, pid)  # 重新导入时先清掉上次的结果
        paper = s.get(BankPaper, pid)
        if not paper.title:
            paper.title = (str(header or "").strip() or "未命名试卷")[:100]
        qids = []
        answer_doc = any(pg.get("kind") == "mixed" for pg in pages)
        for seq, q in enumerate(questions, start=1):
            ans = answers.get(norm_label(q["number_label"]) or "") or {}
            final = ans.get("final", "")
            row = Question(
                subject=subject, origin="bank", content_hash=content_hash(subject, q["stem_md"], q["options"]),
                stem_md=q["stem_md"], options=q["options"], sub_questions=q["sub_questions"],
                figures=[{"kind": "in_crop"}] if q["has_figure"] else None,
                answer={"final": final} if final else None, solution_md=ans.get("solution") or None,
                answer_source="official" if final else "none", question_type=q["type"],
            )
            s.add(row)
            s.flush()
            # 答案版卷子的填空题，横线上一般已经填好了答案
            shown = q["answer_shown"] or (answer_doc and q["type"] == "fill")
            s.add(BankItem(question_id=row.id, paper_id=pid, seq=seq, number_label=q["number_label"],
                           regions=q["regions"], points=q["points"], flags={"answer_in_crop": True} if shown else None))
            qids.append(row.id)
        labels = {norm_label(q["number_label"]) for q in questions}
        paper.pages = pages
        paper.stats = {"unmatched_answers": sorted((k for k in answers if k not in labels), key=int)}
        paper.error = "\n".join(errors) or None
    ctx.bank_index.invalidate()

    handle.progress("分类知识点", 62)
    try:
        _classify(ctx, subject, qids)
    except CostCapExceeded as exc:
        errors.append(f"分类暂停：{exc}")

    if verify:
        verify_paper(ctx, handle, pid, 70, 95)

    handle.progress("匹配已录入的错题", 96)
    matched = rematch_captured(ctx, pid)
    with ctx.db.session() as s:
        paper = s.get(BankPaper, pid)
        paper.error = "\n".join(errors) or None
        paper.status = "ready"
        refresh_stats(s, paper, matched_captured=matched)
        stats = dict(paper.stats or {})
    return stats


def _delete_items(s: "Session", paper_id: str) -> None:
    for item in s.query(BankItem).filter_by(paper_id=paper_id).all():
        s.query(QuestionKp).filter_by(question_id=item.question_id).delete()
        s.delete(item)
        s.flush()
        q = s.get(Question, item.question_id)
        if q is not None:
            s.delete(q)
    s.flush()


def _classify(ctx: "AppContext", subject: str, qids: list[str]) -> None:
    for start in range(0, len(qids), CLASSIFY_BATCH):
        chunk = qids[start:start + CLASSIFY_BATCH]
        with ctx.db.session() as s:
            rows = []
            for idx, qid in enumerate(chunk):
                q = s.get(Question, qid)
                item = s.get(BankItem, qid)
                rows.append({"id": idx, "number_label": item.number_label, "type": q.question_type,
                             "stem": (q.stem_md or "")[:600], "options": q.options})
        try:
            result = ctx.llm.chat_json("classify", prompts.classify_messages(subject, ctx.curriculum, rows),
                                       prompt_version=prompts.CLASSIFY_VERSION)
        except CostCapExceeded:
            raise
        except LLMError as exc:
            log.warning("bank classify failed: %s", exc)
            continue
        with ctx.db.session() as s:
            for item in (result or {}).get("items", []):
                try:
                    qid = chunk[int(item.get("id"))]
                except (TypeError, ValueError, IndexError):
                    continue
                apply_classification(ctx, s, s.get(Question, qid), item)


# ---------------------------------------------------------------- AI 核对官方答案


_ANS_DROP = re.compile(r"[\s$，。、；：,.;:！!？?（）()\[\]{}【】“”\"'^]|\\(?:text|mathrm|rm|quad|,|;|!|left|right)")


def _norm_answer(s: str) -> str:
    t = unicodedata.normalize("NFKC", s or "").lower()
    t = t.replace("\\times", "×").replace("\\cdot", "×").replace("*", "×").replace("\\pi", "π")
    t = t.replace("\\ ", "").replace("_", "")
    t = re.sub(r"\\[dt]?frac\{([^{}]*)\}\{([^{}]*)\}", r"\1/\2", t)
    t = re.sub(r"\\sqrt\{([^{}]*)\}", r"√\1", t)
    return _ANS_DROP.sub("", t)


def answers_agree(official: str, ai: str, qtype: str) -> bool | None:
    """官方答案和 AI 答案是否一致：True 一致，False 不一致（请家长看一眼），None 没法自动比对（如证明题）。"""
    if not official or not ai:
        return None
    if qtype in ("choice_single", "choice_multi"):
        a = set(re.findall(r"[A-D]", unicodedata.normalize("NFKC", official).upper()))
        b = set(re.findall(r"[A-D]", unicodedata.normalize("NFKC", ai).upper()))
        if a and b:
            return a == b
    na, nb = _norm_answer(official), _norm_answer(ai)
    if na == nb or (min(len(na), len(nb)) >= 4 and (na in nb or nb in na)):  # 短答案不按包含算，√3 和 2√3 不同
        return True
    short = max(len(na), len(nb)) <= 12  # 短答案（数值、选项、几个字）不一样就是不一样
    nums_a, nums_b = re.findall(r"\d+(?:\.\d+)?", na), re.findall(r"\d+(?:\.\d+)?", nb)
    if nums_a and nums_b:
        if nums_a == nums_b:
            return True
        if set(nums_a).isdisjoint(nums_b) or short:
            return False
        return None
    return False if short else None


def verify_paper(ctx: "AppContext", handle: JobHandle, paper_id: str, lo: int = 0, hi: int = 100) -> dict:
    """AI 独立解每道还没核对过的题：有官方答案的比对，没有的把 AI 答案标"待核"。"""
    with ctx.db.session() as s:
        paper = s.get(BankPaper, paper_id)
        subject = paper.subject
        todo = [q.id for item, q in s.query(BankItem, Question).join(Question, BankItem.question_id == Question.id)
                .filter(BankItem.paper_id == paper_id).order_by(BankItem.seq)
                if q.verification is None and q.answer_source in ("official", "none")]
    paused = False
    for i, qid in enumerate(todo):
        handle.progress(f"AI 独立解题核对 {i + 1}/{len(todo)}", lo + int(i / max(1, len(todo)) * (hi - lo)))
        with ctx.db.session() as s:
            q = s.get(Question, qid)
            item = s.get(BankItem, qid)
            paper = s.get(BankPaper, paper_id)
            qdata = {"type": q.question_type, "stem": q.stem_md, "options": q.options,
                     "sub_questions": q.sub_questions}
            try:
                url, _ = imaging.data_url_jpeg(question_image(ctx, paper, item.regions))
            except ValueError:
                url = None
        try:
            out = ctx.llm.chat_json("solve", prompts.solve_messages(subject, qdata, url),
                                    prompt_version=prompts.SOLVE_VERSION) or {}
        except CostCapExceeded:
            paused = True
            break
        except LLMError as exc:
            log.warning("bank verify failed for %s: %s", qid, exc)
            continue
        ai = str(out.get("final_answer") or "").strip()
        with ctx.db.session() as s:
            q = s.get(Question, qid)
            ver = {"solver": ctx.llm.models.get("solve"), "ai_answer": ai, "confidence": out.get("confidence"),
                   "at": now_iso()}
            if q.answer_source == "official":
                ver["agree"] = answers_agree((q.answer or {}).get("final", ""), ai, q.question_type)
                if ver["agree"] is not True:
                    ver["ai_solution_md"] = (out.get("solution_md") or "")[:4000]
            elif q.answer_source == "none" and ai:
                q.answer = {"final": ai}
                q.solution_md = out.get("solution_md")
                q.answer_source = "ai_unverified"
            q.verification = ver
    with ctx.db.session() as s:
        paper = s.get(BankPaper, paper_id)
        refresh_stats(s, paper, verify_paused=paused)
        return dict(paper.stats or {})


def refresh_stats(s: "Session", paper: BankPaper, **extra: object) -> None:
    rows = s.query(Question).join(BankItem, BankItem.question_id == Question.id) \
        .filter(BankItem.paper_id == paper.id).all()
    stats = {k: v for k, v in (paper.stats or {}).items() if k in ("unmatched_answers", "matched_captured")}
    stats.update({
        "questions": len(rows),
        "official": sum(q.answer_source in ("official", "manual") for q in rows),
        "ai_only": sum(q.answer_source == "ai_unverified" for q in rows),
        "no_answer": sum(q.answer_source == "none" for q in rows),
        "unchecked": sum(q.answer_source == "official" and q.verification is None for q in rows),
        "to_review": sum(needs_review(q) for q in rows),
        "verify_paused": bool((paper.stats or {}).get("verify_paused")),
    })
    stats.update(extra)
    paper.stats = stats


def needs_review(q: Question) -> bool:
    """官方答案和 AI 答案对不上，家长还没看过。"""
    v = q.verification or {}
    return q.answer_source == "official" and v.get("agree") is False and not v.get("reviewed")


def verify_job(ctx: "AppContext", handle: JobHandle, payload: dict) -> dict:
    return verify_paper(ctx, handle, payload["paper_id"])


def delete_paper(ctx: "AppContext", paper_id: str) -> None:
    with ctx.db.session() as s:
        paper = s.get(BankPaper, paper_id)
        if paper is None:
            raise ValueError("这套卷子不存在")
        _delete_items(s, paper_id)
        s.delete(paper)
    ctx.storage.delete_tree(ctx.storage.bank_dir(paper_id))
    shutil.rmtree(_cache_dir(ctx, paper_id), ignore_errors=True)
    ctx.bank_index.invalidate()


# ---------------------------------------------------------------- 录入时匹配


_STEM_NO = re.compile(r"^\s*(?:第\s*)?\d+\s*(?:题)?\s*[.．、:：)）]?\s*")
_LATEX_CMD = re.compile(r"\\[a-zA-Z]+")
_KEEP = re.compile(r"[\u4e00-\u9fff0-9a-z]")
_NUM = re.compile(r"\d+(?:\.\d+)?")
MIN_FP_LEN = 10
MATCH_THRESHOLD = 0.8


def _match_text(stem: str | None, options: list | None) -> str:
    text = _STEM_NO.sub("", unicodedata.normalize("NFKC", stem or ""), count=1)
    if options:
        text += "".join(unicodedata.normalize("NFKC", str(o.get("md", ""))) for o in options if isinstance(o, dict))
    return _LATEX_CMD.sub("", text).lower()


@dataclass(frozen=True)
class _Entry:
    question_id: str
    bigrams: frozenset[str]
    numbers: tuple[str, ...]


def _entry(qid: str, stem: str | None, options: list | None) -> _Entry | None:
    text = _match_text(stem, options)
    fp = "".join(_KEEP.findall(text))
    if len(fp) < MIN_FP_LEN:
        return None
    return _Entry(qid, frozenset(fp[i:i + 2] for i in range(len(fp) - 1)), tuple(sorted(_NUM.findall(text))))


def similarity(a: _Entry, b: _Entry) -> float:
    """字符二元组的 Dice 系数；题目里的数字必须完全一样（换了数的同类题不算同一道）。"""
    if a.numbers != b.numbers:
        return 0.0
    return 2 * len(a.bigrams & b.bigrams) / (len(a.bigrams) + len(b.bigrams))


class BankIndex:
    """按学科缓存题库里每道题的指纹；导入、删除、修改后作废。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cache: dict[str, list[_Entry]] = {}

    def invalidate(self) -> None:
        with self._lock:
            self._cache.clear()

    def _entries(self, s: "Session", subject: str) -> list[_Entry]:
        with self._lock:
            if subject not in self._cache:
                rows = s.query(Question.id, Question.stem_md, Question.options) \
                    .filter(Question.subject == subject, Question.origin == "bank", Question.status == "active")
                self._cache[subject] = [e for e in (_entry(*r) for r in rows) if e is not None]
            return self._cache[subject]

    def best(self, s: "Session", subject: str, stem: str | None, options: list | None,
             among: set[str] | None = None) -> tuple[str, float] | None:
        probe = _entry("", stem, options)
        if probe is None:
            return None
        best: tuple[str, float] | None = None
        for e in self._entries(s, subject):
            if among is not None and e.question_id not in among:
                continue
            score = similarity(probe, e)
            if score >= MATCH_THRESHOLD and (best is None or score > best[1]):
                best = (e.question_id, score)
        return best


def attach_match(ctx: "AppContext", s: "Session", q: Question, among: set[str] | None = None) -> bool:
    """录入的题如果在题库里：记下出处，带上官方答案、知识点和题位。家长自己填的答案不覆盖。"""
    old = dict(q.bank_match or {})
    if old.get("status") == "rejected":
        return False
    hit = ctx.bank_index.best(s, q.subject, q.stem_md, q.options, among)
    if hit is None:
        return False
    bq = s.get(Question, hit[0])
    if bq is None:
        return False
    prev = {k: old[k] for k in ("prev_answer", "prev_source", "prev_solution") if k in old} or \
        {"prev_answer": q.answer, "prev_source": q.answer_source, "prev_solution": q.solution_md}
    q.bank_match = {"question_id": bq.id, "score": round(hit[1], 3), "status": "auto", **prev}
    if bq.answer and bq.answer_source in ("official", "manual") and q.answer_source != "manual":
        q.answer = dict(bq.answer)
        q.solution_md = bq.solution_md
        q.answer_source = "official"
    if not s.query(QuestionKp).filter_by(question_id=q.id).first():
        for k in s.query(QuestionKp).filter_by(question_id=bq.id).all():
            s.add(QuestionKp(question_id=q.id, kp_code=k.kp_code, is_primary=k.is_primary))
    q.bj_slot = q.bj_slot or bq.bj_slot
    q.difficulty = q.difficulty or bq.difficulty
    return True


def rematch_captured(ctx: "AppContext", paper_id: str) -> int:
    """导入一套卷子后，已经录入的错题如果在里面，补上官方答案。返回对上的题数。"""
    n = 0
    with ctx.db.session() as s:
        paper = s.get(BankPaper, paper_id)
        among = {i.question_id for i in s.query(BankItem).filter_by(paper_id=paper_id)}
        for q in s.query(Question).filter(Question.origin == "captured", Question.subject == paper.subject):
            bm = q.bank_match or {}
            if bm.get("status") == "rejected" or not (q.stem_md or "").strip():
                continue
            if bm.get("question_id") and s.get(Question, bm["question_id"]) is not None:
                continue  # 已经对上了题库里现有的题
            n += attach_match(ctx, s, q, among)
    return n


def reject_match(ctx: "AppContext", question_id: str) -> dict:
    """家长说"不是这道题"：取消匹配，恢复原来的答案；没有答案的错题交给 AI 解答。"""
    with ctx.db.session() as s:
        q = s.get(Question, question_id)
        if q is None:
            raise ValueError("题目不存在")
        bm = dict(q.bank_match or {})
        if bm.get("status") != "auto":
            return {"ok": True}
        if q.answer_source == "official":
            q.answer = bm.get("prev_answer")
            q.answer_source = bm.get("prev_source") or "none"
            q.solution_md = bm.get("prev_solution")
        q.bank_match = {"question_id": bm.get("question_id"), "score": bm.get("score"), "status": "rejected"}
        solve = q.answer_source == "none" and s.query(Mistake).filter_by(question_id=q.id).first() is not None
    if solve:
        ctx.jobs.submit("solve", {"question_id": question_id})
    return {"ok": True, "solving": solve}


def match_info(s: "Session", q: Question) -> dict | None:
    """给页面显示的出处信息。"""
    bm = q.bank_match or {}
    if bm.get("status") != "auto" or not bm.get("question_id"):
        return None
    item = s.get(BankItem, bm["question_id"])
    if item is None:
        return None
    paper = s.get(BankPaper, item.paper_id)
    return {"question_id": item.question_id, "paper_id": paper.id, "paper_title": paper.title,
            "number_label": item.number_label, "score": bm.get("score")}


def register(ctx: "AppContext") -> None:
    ctx.jobs.register("bank_import", import_paper)
    ctx.jobs.register("bank_verify", verify_job)
