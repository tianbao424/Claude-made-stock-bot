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
        crops.append(imaging.crop(img, [x0 / 1000 * w, y0 / 1000 * h, x1 / 1000 * w, y1 / 1000 * h]))
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
        "regions": [region],
    }


def _extend(last: dict, item: dict, region: dict) -> None:
    """跨页（或跨半页）的题：把后半段接到上一道题上。"""
    last["regions"].append(region)
    stem = (item.get("stem_md") or "").strip()
    if stem and stem not in last["stem_md"]:
        last["stem_md"] = (last["stem_md"] + "\n\n" + stem).strip()
    if item.get("sub_questions"):
        last["sub_questions"] = (last["sub_questions"] or []) + list(item["sub_questions"])
    last["has_figure"] = last["has_figure"] or bool(item.get("has_figure"))


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

    questions: list[dict] = []
    answers: dict[str, dict] = {}
    errors: list[str] = []
    header = None
    for i, pg in enumerate(pages):
        handle.progress(f"第 {i + 1}/{len(pages)} 页：识别", 5 + int(i / len(pages) * 55))
        img = page_image(ctx, pid, files, pg)
        text = _page_text(ctx, files, pg)
        kinds = []
        h, w = img.shape[:2]
        for x0, x1, part in _segments(img):
            seg = img[:, int(x0 * w):int(x1 * w)]
            url, _ = imaging.data_url_jpeg(seg)
            try:
                out = ctx.llm.chat_json("bank", prompts.bank_page_messages(subject, url, text, pg["role"], part),
                                        prompt_version=prompts.BANK_PAGE_VERSION) or {}
            except CostCapExceeded:
                raise
            except LLMError as exc:
                errors.append(f"第 {pg['n']} 页识别失败：{exc}")
                continue
            kinds.append(out.get("page_kind"))
            header = header or out.get("header")
            for item in out.get("questions") or []:
                region = {"page": pg["n"], "bbox": _seg_bbox(item.get("bbox"), x0, x1, seg.shape[1], seg.shape[0])}
                same = questions and norm_label(item.get("number_label")) is not None \
                    and norm_label(item.get("number_label")) == norm_label(questions[-1]["number_label"])
                if questions and (item.get("continued") or same):
                    _extend(questions[-1], item, region)
                else:
                    questions.append(_new_question(item, region))
            for item in out.get("answers") or []:
                _merge_answer(answers, item)
        pg["kind"] = next((k for k in ("questions", "answers") if k in kinds), "other")

    if not questions:
        raise RuntimeError("；".join(errors) or "没有识别出题目。请确认上传的是试卷（不是只有答案）")

    handle.progress("保存题目", 60)
    with ctx.db.session() as s:
        _delete_items(s, pid)  # 重新导入时先清掉上次的结果
        paper = s.get(BankPaper, pid)
        if not paper.title:
            paper.title = (str(header or "").strip() or "未命名试卷")[:100]
        qids = []
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
            s.add(BankItem(question_id=row.id, paper_id=pid, seq=seq, number_label=q["number_label"],
                           regions=q["regions"], points=q["points"]))
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
