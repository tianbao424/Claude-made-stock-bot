"""题目相关的小工具：去重哈希、坐标换算、页面图片读取与裁切。"""

import hashlib
import json
import re
import unicodedata
from typing import TYPE_CHECKING

import numpy as np

from app.adapters import imaging
from app.models import QuestionInstance, SourcePage

if TYPE_CHECKING:
    from app.context import AppContext

_PUNCT = re.compile(r"[\s，。、；：？！,.;:?!“”\"'（）()\[\]【】{}<>《》$\\]+")


def content_hash(subject: str, stem_md: str, options: list | None) -> str:
    """规范化题干和选项后求哈希：忽略空白、标点、全半角差异。"""
    text = unicodedata.normalize("NFKC", stem_md or "")
    if options:
        text += "|" + "|".join(unicodedata.normalize("NFKC", str(o.get("md", ""))) for o in options)
    norm = _PUNCT.sub("", text).lower()
    return hashlib.sha256(f"{subject}:{norm}".encode()).hexdigest()


def bbox_to_pixels(bbox: list, width: int, height: int) -> list[float]:
    """把模型给的坐标换成像素。要求的是 0–1000 归一化坐标；若数值超过 1000，按像素坐标理解。"""
    if not isinstance(bbox, list) or len(bbox) != 4:
        return [0.0, 0.0, float(width), float(height)]
    x0, y0, x1, y1 = (float(v) for v in bbox)
    if max(x0, y0, x1, y1) <= 1000:
        x0, x1 = x0 / 1000 * width, x1 / 1000 * width
        y0, y1 = y0 / 1000 * height, y1 / 1000 * height
    x0, x1 = sorted((max(0.0, min(width, x0)), max(0.0, min(width, x1))))
    y0, y1 = sorted((max(0.0, min(height, y0)), max(0.0, min(height, y1))))
    if x1 - x0 < 10 or y1 - y0 < 10:
        return [0.0, 0.0, float(width), float(height)]
    return [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)]


def corrected_image(ctx: "AppContext", page: SourcePage) -> np.ndarray:
    """矫正后的整页（由原图 + 变换矩阵生成，缓存在 .local/cache）。"""
    # 缓存用无损 PNG：反复 JPEG 编码会冲淡细笔画的颜色，影响去手写。缓存键里带上变换矩阵，重新矫正后自动失效。
    key = hashlib.sha1(json.dumps(page.transform, sort_keys=True).encode()).hexdigest()[:10]
    cache = ctx.storage.cache / "pages" / page.id / f"corrected-{key}.png"
    if cache.exists():
        return imaging.decode(cache.read_bytes())
    img = imaging.apply_transform(imaging.decode(ctx.storage.read(page.original_path)), page.transform)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(imaging.encode_png(img))
    return img


def page_image(ctx: "AppContext", page: SourcePage, kind: str) -> np.ndarray:
    if kind == "erased" and page.erased_path and ctx.storage.exists(page.erased_path):
        return imaging.decode(ctx.storage.read(page.erased_path))
    return corrected_image(ctx, page)


def instance_crop(ctx: "AppContext", inst: QuestionInstance, page: SourcePage, kind: str) -> np.ndarray:
    return imaging.crop(page_image(ctx, page, kind), inst.bbox)
