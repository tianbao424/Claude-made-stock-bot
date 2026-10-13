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
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise ValueError("JPEG 编码失败")
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
    im.save(out, "JPEG", quality=quality, optimize=True)
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


def remove_colored_ink(img: np.ndarray, sat_threshold: int = 70) -> np.ndarray:
    """把饱和度高的像素（红笔、蓝笔等彩色笔迹）涂白。黑色笔迹和铅笔去不掉。"""
    flat = flatten_background(img)
    hsv = cv2.cvtColor(flat, cv2.COLOR_BGR2HSV)
    mask = (hsv[:, :, 1] > sat_threshold) & (hsv[:, :, 2] > 60)
    mask = cv2.dilate(mask.astype(np.uint8) * 255, np.ones((3, 3), np.uint8)) > 0
    gray = cv2.cvtColor(flat, cv2.COLOR_BGR2GRAY)
    gray[mask] = 255
    return gray


def crop(img: np.ndarray, bbox: list[float], pad: int = 6) -> np.ndarray:
    h, w = img.shape[:2]
    x0, y0, x1, y1 = (int(round(v)) for v in bbox)
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(w, x1 + pad), min(h, y1 + pad)
    if x1 <= x0 or y1 <= y0:
        raise ValueError(f"empty crop {bbox}")
    return img[y0:y1, x0:x1]


def mask_header(img: np.ndarray, ratio: float = 0.07) -> np.ndarray:
    """送给外部接口前，把页面最上方（通常是姓名、班级、学校所在的卷头）涂白。"""
    out = img.copy()
    out[: int(out.shape[0] * ratio), :] = 255
    return out


def data_url_jpeg(img: np.ndarray, max_side: int = MODEL_SIDE, quality: int = 85) -> tuple[str, float]:
    """缩放后编码为 data URL，返回 URL 和缩放比例（模型坐标 / 缩放比例 = 原图坐标）。"""
    small, scale = resize_max(img, max_side)
    b64 = base64.b64encode(encode_jpeg(small, quality)).decode()
    return f"data:image/jpeg;base64,{b64}", scale
