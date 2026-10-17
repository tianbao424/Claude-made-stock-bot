"""图像处理：压缩、清晰度检查、透视矫正、去阴影、裁切。"""

import base64
import io

import cv2
import numpy as np
from PIL import Image, ImageOps

MAX_SIDE = 2000  # 存进数据仓库的原图长边像素
MODEL_SIDE = 1600  # 送给视觉模型的长边像素


def decode(data: bytes) -> np.ndarray:
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("无法识别的图片格式")
    return img


def encode_jpeg(img: np.ndarray, quality: int = 80) -> bytes:
    # 4:4:4 不做色度抽样：细笔画的颜色是区分"红笔、蓝笔、印刷"的关键信号
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality,
                                         cv2.IMWRITE_JPEG_SAMPLING_FACTOR, cv2.IMWRITE_JPEG_SAMPLING_FACTOR_444])
    if not ok:
        raise ValueError("JPEG 编码失败")
    return buf.tobytes()


def encode_png(img: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", img, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    if not ok:
        raise ValueError("PNG 编码失败")
    return buf.tobytes()


def encode_png_gray(img: np.ndarray) -> bytes:
    gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ok, buf = cv2.imencode(".png", gray, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    if not ok:
        raise ValueError("PNG 编码失败")
    return buf.tobytes()


def normalize_upload(data: bytes, max_side: int = MAX_SIDE, quality: int = 80) -> tuple[bytes, int, int]:
    """按 EXIF 方向摆正、转 RGB、缩放到长边 max_side，返回 JPEG 字节和宽高。"""
    im = Image.open(io.BytesIO(data))
    im = ImageOps.exif_transpose(im).convert("RGB")
    scale = max_side / max(im.size)
    if scale < 1:
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, "JPEG", quality=quality, optimize=True, subsampling=0)  # 4:4:4，保留笔迹颜色
    return out.getvalue(), im.width, im.height


def resize_max(img: np.ndarray, max_side: int) -> tuple[np.ndarray, float]:
    h, w = img.shape[:2]
    scale = min(1.0, max_side / max(h, w))
    if scale < 1:
        img = cv2.resize(img, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)
    return img, scale


def quality_metrics(img: np.ndarray) -> dict:
    """清晰度用拉普拉斯方差衡量（在固定尺寸上算，便于比较）。"""
    small, _ = resize_max(img, 1000)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    return {"blur": round(blur, 1), "brightness": round(float(gray.mean()), 1), "is_blurry": blur < 60}


def _order_corners(pts: np.ndarray) -> np.ndarray:
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]], dtype=np.float32)


def detect_page_transform(img: np.ndarray, min_area_ratio: float = 0.4) -> dict | None:
    """找出照片中纸张的四个角，返回透视矫正参数；找不到就返回 None（按原图处理）。"""
    small, scale = resize_max(img, 1000)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 50, 150)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=2)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    area_total = small.shape[0] * small.shape[1]
    for c in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
        if cv2.contourArea(c) < min_area_ratio * area_total:
            break
        approx = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        if len(approx) != 4:
            continue
        corners = _order_corners(approx.reshape(4, 2).astype(np.float32) / scale)
        # 四角向中心收 1%，避免把纸边外的桌面也拉进来（打印出来会是一圈黑框）
        center = corners.mean(axis=0)
        corners = (center + (corners - center) * 0.985).astype(np.float32)
        tl, tr, br, bl = corners
        width = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
        height = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
        # 已经几乎是整张图时不必矫正
        h, w = img.shape[:2]
        if width > 0.97 * w and height > 0.97 * h:
            return None
        dst = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype=np.float32)
        m = cv2.getPerspectiveTransform(corners, dst)
        return {"m": m.tolist(), "w": width, "h": height}
    return None


def apply_transform(img: np.ndarray, transform: dict | None) -> np.ndarray:
    if not transform:
        return img
    m = np.array(transform["m"], dtype=np.float64)
    return cv2.warpPerspective(img, m, (transform["w"], transform["h"]), flags=cv2.INTER_CUBIC,
                               borderMode=cv2.BORDER_REPLICATE)


def flatten_background(img: np.ndarray) -> np.ndarray:
    """去阴影：用大核中值滤波估计背景，再除以背景，让纸面变成均匀的白色。"""
    out = []
    for ch in cv2.split(img):
        bg = cv2.medianBlur(cv2.dilate(ch, np.ones((7, 7), np.uint8)), 31)
        norm = cv2.divide(ch, bg, scale=255)
        out.append(norm)
    return cv2.merge(out)


def neutralize_ink(flat: np.ndarray, dark_below: int = 110) -> np.ndarray:
    """把拍照带来的偏色从深色像素上去掉，让印刷的黑字真的是灰色的。

    去阴影只能把纸面（白色）校正回来；在暖光或台灯下拍的照片里，黑色印刷字会偏棕、偏橙，
    在 HSV 里饱和度比红笔还高，原来会被整页当成彩色笔迹擦掉（2026-10 家长拍的一页卷子，
    印刷字只剩下 6%）。一页卷子上最深的像素绝大多数是印刷字，所以用它们的中位颜色估计偏色，
    每个通道各用一条幂曲线（白色 255 不动、把这个中位数拉到灰色）校正。
    红笔、蓝笔的颜色和印刷字的偏色方向不同，校正后仍然是明显的彩色。
    """
    gray = cv2.cvtColor(flat, cv2.COLOR_BGR2GRAY)
    dark = gray < dark_below
    if dark.sum() < 500:  # 几乎没有深色内容（空白页），没什么可估计的
        return flat
    # 用"每个像素的通道差"的中位数估计偏色，而不是每个通道各取中位数：
    # 红笔占深色像素两成时，各通道单独取中位数会把红色通道抬高，反而给黑字染上颜色。
    b, g, r = (flat[:, :, c][dark].astype(np.int16) for c in range(3))
    level = float(np.median(g))
    med = np.array([level + np.median(b - g), level, level + np.median(r - g)])
    if med.max() - med.min() < 12:  # 本来就是灰的，不用动
        return flat
    target = max(float(med.mean()), 1.0)
    out = []
    for c in range(3):
        gamma = float(np.clip(np.log(target / 255) / np.log(max(med[c], 1.0) / 255), 0.5, 2.0))
        lut = np.clip(255 * (np.arange(256) / 255) ** gamma, 0, 255).astype(np.uint8)
        out.append(cv2.LUT(flat[:, :, c], lut))
    return cv2.merge(out)


def _printed_color(strong: np.ndarray, min_radius: float = 6.0, area_radius: float = 4.5, min_area: int = 300) -> np.ndarray:
    """彩色像素里哪些是印刷的图，而不是笔迹。

    笔迹是细线：红笔、蓝笔在 2000 像素宽的页面上粗 3–6 像素。印刷的彩色图（禁止吸烟标志、
    滑梯插画、黄色小灯泡、蓝色滑动变阻器）总有大块填充，或者虽小但比笔画粗。
    按连通块算最粗处的半径（距离变换），够粗的整块保留，笔迹压在图上也随图保留（图不能缺一块）。
    """
    n, labels, stats, _ = cv2.connectedComponentsWithStats(strong, connectivity=8)
    if n <= 1:
        return np.zeros(strong.shape, bool)
    dist = cv2.distanceTransform(strong, cv2.DIST_L2, 5)
    radius = np.zeros(n, np.float32)
    np.maximum.at(radius, labels.ravel(), dist.ravel())
    area = stats[:, cv2.CC_STAT_AREA]
    keep = (radius >= min_radius) | ((radius >= area_radius) & (area >= min_area))
    keep[0] = False
    return keep[labels]


def remove_colored_ink(img: np.ndarray, sat_threshold: int = 70) -> np.ndarray:
    """把彩色笔迹（红笔、蓝笔等）涂白。黑色笔迹和铅笔去不掉。

    笔画边缘因为抗锯齿颜色变淡、饱和度变低，单用一个阈值会留下一圈"鬼影"，
    所以在明显的彩色笔画附近，再把饱和度较低的像素和发灰的残留一起清掉。
    """
    flat = neutralize_ink(flatten_background(img))
    hsv = cv2.cvtColor(flat, cv2.COLOR_BGR2HSV)
    sat, val = hsv[:, :, 1], hsv[:, :, 2]
    strong = ((sat > sat_threshold) & (val > 60)).astype(np.uint8)
    strong[_printed_color(strong)] = 0  # 彩色的印刷图（物理卷的实物图、电路元件、标志）不是笔迹
    near = cv2.dilate(strong, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))) > 0
    weak = (sat > sat_threshold // 3) & (val > 40)
    mask = (strong > 0) | (weak & near)
    mask = cv2.dilate(mask.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    gray = cv2.cvtColor(flat, cv2.COLOR_BGR2GRAY)
    # 深色、不带颜色的是印刷内容，不动它。深色像素的 HSV 饱和度是"通道差 / 最大通道"，
    # 很小的通道差也会算出很高的饱和度，所以这里按通道差本身判断
    chroma = flat.max(axis=2).astype(np.int16) - flat.min(axis=2).astype(np.int16)
    printed = (gray < 110) & (chroma < 45)
    gray[mask & ~printed] = 255
    gray[near & (gray > 150)] = 255  # 笔画附近发灰的残留
    return gray


def crop(img: np.ndarray, bbox: list[float], pad: int = 6) -> np.ndarray:
    h, w = img.shape[:2]
    x0, y0, x1, y1 = (int(round(v)) for v in bbox)
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(w, x1 + pad), min(h, y1 + pad)
    if x1 <= x0 or y1 <= y0:
        raise ValueError(f"empty crop {bbox}")
    return img[y0:y1, x0:x1]


def mask_header(img: np.ndarray, ratio: float) -> np.ndarray:
    """送给外部接口前，把页面最上方（通常是姓名、班级、学校所在的卷头）涂白。"""
    out = img.copy()
    out[: int(out.shape[0] * ratio), :] = 255
    return out


def data_url_jpeg(img: np.ndarray, max_side: int = MODEL_SIDE, quality: int = 85) -> tuple[str, float]:
    """缩放后编码为 data URL，返回 URL 和缩放比例（模型坐标 / 缩放比例 = 原图坐标）。"""
    small, scale = resize_max(img, max_side)
    b64 = base64.b64encode(encode_jpeg(small, quality)).decode()
    return f"data:image/jpeg;base64,{b64}", scale
