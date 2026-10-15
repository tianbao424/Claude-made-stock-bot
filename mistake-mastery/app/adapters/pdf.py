"""PDF：数页数、把一页渲染成图片、取文字层（pypdfium2）。"""

import threading
from dataclasses import dataclass, field

import cv2
import numpy as np
import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c

# pdfium 不是线程安全的，后台任务有两个线程，所有调用串行化
_lock = threading.Lock()


class PdfError(ValueError):
    pass


def is_pdf(data: bytes) -> bool:
    return data[:1024].lstrip().startswith(b"%PDF")


def _open(data: bytes) -> pdfium.PdfDocument:
    try:
        return pdfium.PdfDocument(data)
    except pdfium.PdfiumError as exc:
        raise PdfError(f"PDF 打不开（文件损坏或有密码）：{exc}") from exc


def page_count(data: bytes) -> int:
    with _lock:
        doc = _open(data)
        try:
            return len(doc)
        finally:
            doc.close()


def render_page(data: bytes, index: int, max_side: int = 2000) -> np.ndarray:
    """渲染成 BGR 图片，长边约 max_side 像素（A4 约相当于 170 DPI）。"""
    with _lock:
        doc = _open(data)
        try:
            page = doc[index]
            w, h = page.get_size()
            scale = min(max_side / max(w, h), 4.0)
            pil = page.render(scale=scale, fill_color=(255, 255, 255, 255)).to_pil().convert("RGB")
        finally:
            doc.close()
    return cv2.cvtColor(np.asarray(pil), cv2.COLOR_RGB2BGR)


def page_text(data: bytes, index: int, limit: int = 6000) -> str:
    """PDF 自带的文字层（Word 导出的卷子通常有；扫描件没有，返回空串）。"""
    with _lock:
        doc = _open(data)
        try:
            page = doc[index]
            text = page.get_textpage().get_text_range()
        finally:
            doc.close()
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()[:limit]


# ---------------------------------------------------------------- 版面：文字行和图片的位置


@dataclass
class Line:
    """一行文字。坐标按页面归一化到 0–1000，左上角为原点。"""

    y0: float
    y1: float
    x0: float
    x1: float
    text: str


@dataclass
class Layout:
    lines: list[Line] = field(default_factory=list)
    images: list[tuple[float, float, float, float]] = field(default_factory=list)  # (x0, y0, x1, y1)


def page_layout(data: bytes, index: int) -> Layout:
    """从文字层取出每行文字的位置，以及图片的位置（Word / WPS 导出的 PDF 都有；扫描件为空）。"""
    with _lock:
        doc = _open(data)
        try:
            page = doc[index]
            w, h = page.get_size()
            tp = page.get_textpage()
            chars = []
            for i in range(tp.count_chars()):
                ch = tp.get_text_range(i, 1)
                if not ch.strip():
                    continue
                left, bottom, right, top = tp.get_charbox(i)
                if right <= left and top <= bottom:
                    continue
                chars.append((ch, left / w * 1000, (h - top) / h * 1000, right / w * 1000, (h - bottom) / h * 1000))
            images = []
            for obj in page.get_objects(max_depth=2):
                if obj.type == pdfium_c.FPDF_PAGEOBJ_IMAGE:
                    left, bottom, right, top = obj.get_bounds()
                    images.append((left / w * 1000, (h - top) / h * 1000, right / w * 1000, (h - bottom) / h * 1000))
        finally:
            doc.close()
    # 按竖直位置把字符归到行：字符的中线落在某一行的上下范围内就算这一行（上下标、细笔画也能归进去）
    rows: list[list] = []  # [y0, y1, x0, x1, [(x, ch)]]
    for ch, x0, y0, x1, y1 in chars:
        mid = (y0 + y1) / 2
        for r in rows:
            if r[0] - 2 <= mid <= r[1] + 2 and not (x0 >= r[2] and x1 <= r[3] and len(r[4]) > 3 and abs(mid - (r[0] + r[1]) / 2) > 6):
                r[0], r[1], r[2], r[3] = min(r[0], y0), max(r[1], y1), min(r[2], x0), max(r[3], x1)
                r[4].append((x0, ch))
                break
        else:
            rows.append([y0, y1, x0, x1, [(x0, ch)]])
    lines = [Line(round(r[0], 1), round(r[1], 1), round(r[2], 1), round(r[3], 1), "".join(c for _, c in sorted(r[4])))
             for r in rows]
    lines.sort(key=lambda ln: (ln.y0, ln.x0))
    return Layout(lines, images)
