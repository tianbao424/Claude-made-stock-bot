"""打印排版（见 docs/03 §10）：先装箱再渲染，确定性分页，输出 PDF + 版面清单。

v0.1 的打印内容都是图片块（擦除后的整页或题目截图），尺寸事先就知道，所以直接在
Python 里装箱，不需要先用浏览器测量。之后加入文字排版的变式题时再引入"测量"步骤。
"""

import base64
import html
import io
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
import qrcode

from app.adapters import imaging
from app.ids import now_iso, today_str
from app.jobs import JobHandle
from app.models import Mistake, PrintJob, PrintJobItem, Question, QuestionInstance, SourceDocument, SourcePage
from app.services.questions import instance_crop, page_image

if TYPE_CHECKING:
    from app.context import AppContext

log = logging.getLogger(__name__)

PAGE_W, PAGE_H = 210.0, 297.0  # A4，毫米
MARGIN_X = 12.0
CONTENT_TOP = 20.0
CONTENT_BOTTOM = PAGE_H - 18.0
CONTENT_W = PAGE_W - 2 * MARGIN_X
CONTENT_H = CONTENT_BOTTOM - CONTENT_TOP
BLOCK_GAP = 4.0
LABEL_H = 6.0

TEMPLATES = {"page_restore": "原卷还原", "redo_sheet": "错题重做单"}
SUBJECT_NAMES = {"math": "数学", "physics": "物理"}


# ---------------------------------------------------------------- 装箱


@dataclass
class Block:
    seq: int
    label: str
    img: np.ndarray
    width_mm: float  # 期望宽度（按原卷尺寸换算）
    extra_mm: float = 0.0  # 额外留白
    item: dict = field(default_factory=dict)

    @property
    def aspect(self) -> float:
        h, w = self.img.shape[:2]
        return h / w


@dataclass
class Placed:
    block: Block
    x: float
    y: float
    w: float
    h: float  # 图片高度（不含标签和额外留白）


def pack(blocks: list[Block]) -> list[list[Placed]]:
    """按顺序把题块装进页面，一道题不跨页；超高的题单独一页并等比缩小。"""
    pages: list[list[Placed]] = [[]]
    y = CONTENT_TOP
    for b in blocks:
        w = min(b.width_mm, CONTENT_W)
        h = w * b.aspect
        total = LABEL_H + h + b.extra_mm
        if total > CONTENT_H:  # 一页都放不下：缩小到正好一页
            scale = (CONTENT_H - LABEL_H - b.extra_mm) / h
            w, h = w * scale, h * scale
            total = CONTENT_H
        if y + total > CONTENT_BOTTOM + 0.01 and pages[-1]:
            pages.append([])
            y = CONTENT_TOP
        pages[-1].append(Placed(b, MARGIN_X, y, w, h))
        y += total + BLOCK_GAP
    return [p for p in pages if p] or [[]]


def fit_full_page(img: np.ndarray) -> tuple[float, float, float, float]:
    """整页图片等比放进内容区，居中。返回 x, y, w, h（毫米）。"""
    h_px, w_px = img.shape[:2]
    scale = min(CONTENT_W / w_px, CONTENT_H / h_px)
    w, h = w_px * scale, h_px * scale
    return MARGIN_X + (CONTENT_W - w) / 2, CONTENT_TOP, w, h


def split_landscape(img: np.ndarray) -> list[np.ndarray]:
    """A3 横版双栏的卷子拆成左右两半，各占一页 A4，字号接近原卷。"""
    h, w = img.shape[:2]
    if w / h < 1.15:
        return [img]
    mid = w // 2
    return [img[:, :mid], img[:, mid:]]


# ---------------------------------------------------------------- 渲染


def _data_url_png(img: np.ndarray) -> str:
    return "data:image/png;base64," + base64.b64encode(imaging.encode_png_gray(img)).decode()


def _qr_data_url(text: str) -> str:
    qr = qrcode.QRCode(border=1, box_size=6)
    qr.add_data(text)
    buf = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


CSS = """
@page { size: 210mm 297mm; margin: 0; }
* { box-sizing: border-box; }
body { margin: 0; font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", "WenQuanYi Zen Hei", sans-serif; color: #000; }
.page { position: relative; width: 210mm; height: 297mm; overflow: hidden; page-break-after: always; }
.page:last-child { page-break-after: auto; }
.abs { position: absolute; }
.hdr { left: 12mm; right: 12mm; top: 8mm; height: 9mm; border-bottom: 0.3mm solid #000; font-size: 10pt;
       display: flex; justify-content: space-between; align-items: flex-end; padding-bottom: 1mm; }
.ftr { left: 12mm; right: 12mm; bottom: 5mm; height: 11mm; font-size: 8.5pt; display: flex;
       justify-content: space-between; align-items: center; }
.ftr img { height: 11mm; width: 11mm; }
.mark { width: 4mm; height: 4mm; background: #000; }
.lbl { font-size: 9.5pt; font-weight: bold; height: 6mm; line-height: 6mm; }
.blk img { display: block; }
.extra { border: 0.2mm dashed #888; }
.key { padding: 20mm 14mm; font-size: 10.5pt; line-height: 1.7; }
.key h2 { font-size: 13pt; margin: 0 0 4mm; }
.key .src { color: #555; font-size: 9pt; }
"""


def _page_html(n: int, total: int, title: str, right: str, qr: str, body: str) -> str:
    marks = "".join(
        f'<div class="abs mark" style="{pos}"></div>'
        for pos in ("left:3mm;top:3mm", "right:3mm;top:3mm", "left:3mm;bottom:3mm", "right:3mm;bottom:3mm"))
    return f"""<section class="page">{marks}
<div class="abs hdr"><span>学透 · {html.escape(title)}</span><span>{html.escape(right)}</span></div>
{body}
<div class="abs ftr"><span>第 {n}/{total} 页 · 做完后扫码回填结果</span><img src="{qr}" alt=""></div>
</section>"""


def render_pdf(ctx: "AppContext", html_doc: str, out_path) -> None:  # noqa: ANN001
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        kwargs = {"executable_path": ctx.settings.chromium_path} if ctx.settings.chromium_path else {}
        browser = p.chromium.launch(**kwargs)
        try:
            page = browser.new_page()
            page.set_content(html_doc, wait_until="load")
            page.pdf(path=str(out_path), width="210mm", height="297mm", print_background=True,
                     margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        finally:
            browser.close()


# ---------------------------------------------------------------- 打印任务


def create_print_job(ctx: "AppContext", *, student_id: str, template: str, base_url: str,
                     document_id: str | None = None, mistake_ids: list[str] | None = None,
                     layout: dict | None = None) -> tuple[str, str]:
    if template not in TEMPLATES:
        raise ValueError(f"未知的打印模板：{template}")
    layout = {"paper": "A4", "split_landscape": True, "extra_space_mm": 0, "with_key": False, **(layout or {})}
    with ctx.db.session() as s:
        job = PrintJob(student_id=student_id, template=template, layout=layout, status="queued",
                       filters={"document_id": document_id, "mistake_ids": mistake_ids})
        s.add(job)
        s.flush()
        if template == "page_restore":
            if not document_id:
                raise ValueError("原卷还原需要指定来源卷")
            doc = s.get(SourceDocument, document_id)
            if doc is None:
                raise ValueError("来源卷不存在")
            job.title = f"原卷还原 · {doc.title or SUBJECT_NAMES.get(doc.subject, '')}"
            pages = s.query(SourcePage).filter_by(document_id=document_id).order_by(SourcePage.page_no).all()
            for seq, pg in enumerate(pages, start=1):
                s.add(PrintJobItem(print_job_id=job.id, seq=seq, page_id=pg.id))
        else:
            if not mistake_ids:
                raise ValueError("请至少选择一道错题")
            job.title = f"错题重做单 · {len(mistake_ids)} 题"
            for seq, mid in enumerate(mistake_ids, start=1):
                m = s.get(Mistake, mid)
                if m is None or m.student_id != student_id:
                    raise ValueError(f"错题不存在：{mid}")
                s.add(PrintJobItem(print_job_id=job.id, seq=seq, mistake_id=m.id, question_id=m.question_id,
                                   instance_id=m.first_instance_id))
        job_id = job.id
    task_id = ctx.jobs.submit("render", {"print_job_id": job_id, "base_url": base_url})
    return job_id, task_id


def render_job(ctx: "AppContext", handle: JobHandle, payload: dict) -> dict:
    try:
        return _render(ctx, handle, payload)
    except Exception as exc:
        with ctx.db.session() as s:
            job = s.get(PrintJob, payload["print_job_id"])
            job.status = "failed"
            job.error = str(exc)[:1000]
        raise


def _render(ctx: "AppContext", handle: JobHandle, payload: dict) -> dict:
    job_id = payload["print_job_id"]
    qr = _qr_data_url(f"{payload.get('base_url', '').rstrip('/')}/p/{job_id}")
    with ctx.db.session() as s:  # 先提交状态，再汇报进度：同时开着两个写事务会让 SQLite 锁住
        job = s.get(PrintJob, job_id)
        job.status = "rendering"
        template, layout, title = job.template, dict(job.layout), job.title or ""
    handle.progress("准备图片", 10)
    with ctx.db.session() as s:
        items = s.query(PrintJobItem).filter_by(print_job_id=job_id).order_by(PrintJobItem.seq).all()
        if template == "page_restore":
            pages_html, manifest, key_items = _build_page_restore(ctx, s, items, layout, title, qr)
        else:
            pages_html, manifest, key_items = _build_redo_sheet(ctx, s, items, layout, title, qr)
        for it in items:
            loc = manifest["items"].get(str(it.seq))
            if loc:
                it.page_no = loc["page"]
                it.answer_bbox_mm = loc["bbox_mm"]
    doc_html = f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>" \
               + "".join(pages_html) + (_answer_key_html(key_items, title) if layout.get("with_key") else "") \
               + "</body></html>"
    handle.progress("生成 PDF", 60)
    out = ctx.storage.pdf / f"{job_id}.pdf"
    render_pdf(ctx, doc_html, out)
    with ctx.db.session() as s:
        job = s.get(PrintJob, job_id)
        job.status = "ready"
        job.pdf_path = str(out.relative_to(ctx.storage.root))
        job.page_count = len(pages_html)
        job.manifest = {"pages": manifest["pages"], "rendered_at": now_iso()}
    return {"pages": len(pages_html)}


def _build_page_restore(ctx, s, items, layout, title, qr):  # noqa: ANN001
    images: list[tuple[int, np.ndarray]] = []
    for it in items:
        pg = s.get(SourcePage, it.page_id)
        img = page_image(ctx, pg, "erased")
        parts = split_landscape(img) if layout.get("split_landscape", True) else [img]
        images += [(it.seq, part) for part in parts]
    total = len(images)
    pages_html, manifest = [], {"pages": [], "items": {}}
    for n, (seq, img) in enumerate(images, start=1):
        x, y, w, h = fit_full_page(img)
        body = f'<img class="abs" src="{_data_url_png(img)}" style="left:{x:.2f}mm;top:{y:.2f}mm;width:{w:.2f}mm;height:{h:.2f}mm">'
        pages_html.append(_page_html(n, total, title, today_str(), qr, body))
        manifest["pages"].append({"no": n, "items": [seq]})
        manifest["items"].setdefault(str(seq), {"page": n, "bbox_mm": [round(v, 2) for v in (x, y, w, h)]})
    return pages_html, manifest, []


def _paper_width_mm(pg: SourcePage) -> float:
    """原卷整页的物理宽度：竖版按 A4/8K 估 210mm，横版双栏按 A3 估 420mm。"""
    known = {"A4": 210.0, "B4": 257.0, "8K": 260.0, "A3": 420.0}
    if pg.paper_size in known:
        return known[pg.paper_size]
    return 420.0 if pg.width > pg.height * 1.15 else 210.0


def _build_redo_sheet(ctx, s, items, layout, title, qr):  # noqa: ANN001
    blocks: list[Block] = []
    key_items: list[dict] = []
    for it in items:
        inst = s.get(QuestionInstance, it.instance_id)
        pg = s.get(SourcePage, inst.page_id)
        q = s.get(Question, it.question_id)
        doc = s.get(SourceDocument, pg.document_id)
        img = instance_crop(ctx, inst, pg, "erased")
        corrected_w = (pg.transform or {}).get("w") or pg.width
        width_mm = (img.shape[1] / corrected_w) * _paper_width_mm(pg)
        origin = f"原第 {inst.number_label} 题" if inst.number_label else "原题"
        label = f"{it.seq}.  {origin} · {doc.title or SUBJECT_NAMES.get(doc.subject, '')}"
        blocks.append(Block(it.seq, label, img, width_mm, float(layout.get("extra_space_mm") or 0)))
        key_items.append({"seq": it.seq, "answer": (q.answer or {}).get("final"), "source": q.answer_source,
                          "solution": q.solution_md})
    placed_pages = pack(blocks)
    total = len(placed_pages)
    pages_html, manifest = [], {"pages": [], "items": {}}
    for n, placed in enumerate(placed_pages, start=1):
        parts = []
        for pl in placed:
            parts.append(
                f'<div class="abs blk" style="left:{pl.x:.2f}mm;top:{pl.y:.2f}mm;width:{CONTENT_W:.2f}mm">'
                f'<div class="lbl">{html.escape(pl.block.label)}</div>'
                f'<img src="{_data_url_png(pl.block.img)}" style="width:{pl.w:.2f}mm;height:{pl.h:.2f}mm">'
                + (f'<div class="extra" style="height:{pl.block.extra_mm:.2f}mm"></div>' if pl.block.extra_mm else "")
                + "</div>")
            manifest["items"][str(pl.block.seq)] = {
                "page": n, "bbox_mm": [round(pl.x, 2), round(pl.y + LABEL_H, 2), round(pl.w, 2),
                                       round(pl.h + pl.block.extra_mm, 2)]}
        manifest["pages"].append({"no": n, "items": [pl.block.seq for pl in placed]})
        pages_html.append(_page_html(n, total, title, today_str(), qr, "".join(parts)))
    return pages_html, manifest, key_items


SOURCE_LABEL = {"teacher": "老师给的答案", "answer_key": "答案页", "manual": "家长填写",
                "ai_unverified": "AI 生成 · 待核", "ai_verified": "AI 生成 · 已交叉校验", "none": "暂无答案"}


def _answer_key_html(items: list[dict], title: str) -> str:
    rows = []
    for it in items:
        ans = html.escape(it["answer"] or "（暂无）")
        src = SOURCE_LABEL.get(it["source"], it["source"])
        rows.append(f"<p><b>{it['seq']}.</b> {ans} <span class='src'>（{src}）</span></p>")
    return f"<section class='page key'><h2>答案 · {html.escape(title)}</h2>{''.join(rows)}</section>"


def register(ctx: "AppContext") -> None:
    ctx.jobs.register("render", render_job)
