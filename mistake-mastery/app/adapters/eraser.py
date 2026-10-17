"""去手写：可切换的接口适配器。

各家接口的请求格式按公开文档实现，返回结果里的图片字段名各不相同，统一用
``find_image`` 在返回的 JSON 里找出图片。具体地址和参数以控制台文档为准，
第 0 步会用 ``python -m app.tools.bakeoff`` 在真实卷子上逐家验证。
"""

import base64
import hashlib
import json
import threading
import time
import uuid
from typing import Any, Protocol

import httpx

from app.adapters import imaging
from app.config import Settings

PNG_MAGIC = b"\x89PNG"
JPEG_MAGIC = b"\xff\xd8\xff"


class EraseError(RuntimeError):
    pass


class Eraser(Protocol):
    name: str

    def erase(self, image: bytes) -> bytes:
        """输入一页图片（JPEG/PNG 字节），返回擦除手写后的图片字节。"""


def find_image(obj: Any) -> bytes | None:
    """在接口返回的 JSON 里找第一张 base64 编码的 PNG/JPEG 图片。"""
    if isinstance(obj, str) and len(obj) > 200:
        s = obj.split(",", 1)[1] if obj.startswith("data:") else obj
        try:
            raw = base64.b64decode(s, validate=False)
        except (ValueError, TypeError):
            return None
        if raw.startswith(PNG_MAGIC) or raw.startswith(JPEG_MAGIC):
            return raw
        return None
    if isinstance(obj, dict):
        for v in obj.values():
            if (found := find_image(v)) is not None:
                return found
    if isinstance(obj, list):
        for v in obj:
            if (found := find_image(v)) is not None:
                return found
    return None


def _raise_if_error(data: dict, vendor: str) -> None:
    for key in ("error_code", "errorCode", "code"):
        code = data.get(key)
        if code not in (None, 0, "0", 200, "200"):
            msg = data.get("error_msg") or data.get("message") or data.get("msg") or json.dumps(data)[:300]
            raise EraseError(f"{vendor} 返回错误 {code}: {msg}")


class NoneEraser:
    """不擦除，原样返回（用于对比，或先用夸克扫描王处理过的图片）。"""

    name = "none"

    def erase(self, image: bytes) -> bytes:
        return image


class LocalColorEraser:
    """本地算法：只能去掉红笔、蓝笔等彩色笔迹并去阴影，黑色笔迹和铅笔去不掉。没有接口密钥时的兜底。"""

    name = "local_color"

    def erase(self, image: bytes) -> bytes:
        img = imaging.decode(image)
        return imaging.encode_png_gray(imaging.remove_colored_ink(img))


class BaiduEraser:
    name = "baidu"
    TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"

    def __init__(self, api_key: str, secret_key: str, url: str, client: httpx.Client | None = None):
        if not (api_key and secret_key):
            raise EraseError("缺少百度接口密钥（XT_BAIDU_API_KEY / XT_BAIDU_SECRET_KEY）")
        self.api_key, self.secret_key, self.url = api_key, secret_key, url
        self.client = client or httpx.Client(timeout=60)
        self._token: tuple[str, float] | None = None
        self._lock = threading.Lock()

    def _access_token(self) -> str:
        with self._lock:
            if self._token and self._token[1] > time.time() + 60:
                return self._token[0]
            r = self.client.post(self.TOKEN_URL, params={
                "grant_type": "client_credentials", "client_id": self.api_key, "client_secret": self.secret_key})
            r.raise_for_status()
            data = r.json()
            if "access_token" not in data:
                raise EraseError(f"百度获取 access_token 失败：{data}")
            self._token = (data["access_token"], time.time() + int(data.get("expires_in", 86400)))
            return self._token[0]

    def erase(self, image: bytes) -> bytes:
        r = self.client.post(self.url, params={"access_token": self._access_token()},
                             data={"image": base64.b64encode(image).decode()},
                             headers={"Content-Type": "application/x-www-form-urlencoded"})
        r.raise_for_status()
        data = r.json()
        _raise_if_error(data, "百度")
        found = find_image(data)
        if found is None:
            raise EraseError(f"百度返回中没有找到图片：{json.dumps(data)[:300]}")
        return found


class YoudaoEraser:
    name = "youdao"

    def __init__(self, app_key: str, app_secret: str, url: str, client: httpx.Client | None = None):
        if not (app_key and app_secret):
            raise EraseError("缺少有道接口密钥（XT_YOUDAO_APP_KEY / XT_YOUDAO_APP_SECRET）")
        self.app_key, self.app_secret, self.url = app_key, app_secret, url
        self.client = client or httpx.Client(timeout=60)

    @staticmethod
    def _truncate(q: str) -> str:
        return q if len(q) <= 20 else q[:10] + str(len(q)) + q[-10:]

    def erase(self, image: bytes) -> bytes:
        q = base64.b64encode(image).decode()
        salt, curtime = str(uuid.uuid4()), str(int(time.time()))
        sign = hashlib.sha256((self.app_key + self._truncate(q) + salt + curtime + self.app_secret).encode()).hexdigest()
        r = self.client.post(self.url, data={
            "q": q, "appKey": self.app_key, "salt": salt, "curtime": curtime, "signType": "v3", "sign": sign})
        r.raise_for_status()
        data = r.json()
        _raise_if_error(data, "有道")
        found = find_image(data)
        if found is None:
            raise EraseError(f"有道返回中没有找到图片：{json.dumps(data)[:300]}")
        return found


class TextInEraser:
    name = "textin"

    def __init__(self, app_id: str, secret_code: str, url: str, client: httpx.Client | None = None):
        if not (app_id and secret_code):
            raise EraseError("缺少 TextIn 接口密钥（XT_TEXTIN_APP_ID / XT_TEXTIN_SECRET_CODE）")
        self.app_id, self.secret_code, self.url = app_id, secret_code, url
        self.client = client or httpx.Client(timeout=60)

    def erase(self, image: bytes) -> bytes:
        r = self.client.post(self.url, content=image, headers={
            "x-ti-app-id": self.app_id, "x-ti-secret-code": self.secret_code,
            "Content-Type": "application/octet-stream"})
        r.raise_for_status()
        data = r.json()
        _raise_if_error(data, "TextIn")
        found = find_image(data)
        if found is None:
            raise EraseError(f"TextIn 返回中没有找到图片：{json.dumps(data)[:300]}")
        return found


def make_eraser(settings: Settings, name: str | None = None) -> Eraser:
    name = name or settings.eraser
    if name == "none":
        return NoneEraser()
    if name == "local_color":
        return LocalColorEraser()
    if name == "baidu":
        return BaiduEraser(settings.baidu_api_key, settings.baidu_secret_key, settings.baidu_erase_url)
    if name == "youdao":
        return YoudaoEraser(settings.youdao_app_key, settings.youdao_app_secret, settings.youdao_erase_url)
    if name == "textin":
        return TextInEraser(settings.textin_app_id, settings.textin_secret_code, settings.textin_erase_url)
    raise ValueError(f"未知的擦除接口：{name}")
