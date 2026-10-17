"""本地 OCR（RapidOCR，ONNX 模型随安装包一起装，不联网）：给照片一个"文字层"。

切题时视觉大模型负责认题（题号、文字、作答、批改），但它给的位置经常差一两行甚至一整题
（2026-10 用 deepseek-flash 录一份物理期中卷，框 17 题框到的是 16 题的选项）。
题库导入用 PDF 的文字层按题号那一行锚定位置；照片没有文字层，就用 OCR 造一个，
再走同一套锚定（bank._anchor_question）。只用到每行文字的位置和开头几个字，不要求全对。
"""

import logging
import threading

import numpy as np

from app.adapters import imaging
from app.adapters.pdf import Layout, Line

log = logging.getLogger(__name__)
_lock = threading.Lock()
_engine = None
_failed = False


def available() -> bool:
    try:
        import rapidocr_onnxruntime  # noqa: F401
    except ImportError:
        return False
    return True


def _get_engine():  # noqa: ANN202
    global _engine, _failed
    with _lock:
        if _engine is None and not _failed:
            try:
                from rapidocr_onnxruntime import RapidOCR
                _engine = RapidOCR()
            except Exception as exc:  # noqa: BLE001 —— 没装或模型加载失败：退回只用模型的框
                _failed = True
                log.warning("本地 OCR 不可用，切题位置只能用模型给的框：%s", exc)
        return _engine


def page_layout(img: np.ndarray) -> Layout | None:
    """整页识别，返回每行文字的位置（0–1000 归一化）；OCR 不可用时返回 None。"""
    engine = _get_engine()
    if engine is None:
        return None
    small, scale = imaging.resize_max(img, 2000)
    h, w = small.shape[:2]
    with _lock:  # 引擎不保证线程安全
        result, _ = engine(small)
    lines = []
    for box, text, _conf in result or []:
        xs, ys = [p[0] for p in box], [p[1] for p in box]
        if not (text or "").strip():
            continue
        lines.append(Line(y0=min(ys) / h * 1000, y1=max(ys) / h * 1000, x0=min(xs) / w * 1000, x1=max(xs) / w * 1000,
                          text=text.strip()))
    lines.sort(key=lambda ln: (ln.y0, ln.x0))
    return Layout(lines=lines)
