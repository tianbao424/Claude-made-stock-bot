"""PDF：数页数、把一页渲染成图片、取文字层（pypdfium2）。"""

import threading

import cv2
import numpy as np
import pypdfium2 as pdfium

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
