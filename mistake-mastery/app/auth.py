"""家庭密码登录：签名会话 Cookie + 登录限速 + 退出所有设备。"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import HTTPException, Request

COOKIE_NAME = "xt_session"
SESSION_DAYS = 30
MAX_FAILURES = 5
LOCK_SECONDS = 15 * 60


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, *, plain: str, hashed: str) -> bool:
    if hashed:
        try:
            _, salt_hex, digest_hex = hashed.split("$")
        except ValueError:
            return False
        expected = hash_password(password, salt=bytes.fromhex(salt_hex)).split("$")[2]
        return hmac.compare_digest(expected, digest_hex)
    if plain:
        return hmac.compare_digest(password.encode(), plain.encode())
    return False


def load_secret_key(local_dir: Path) -> bytes:
    path = local_dir / "secret_key"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(secrets.token_hex(32))
        path.chmod(0o600)
    return bytes.fromhex(path.read_text().strip())


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def make_token(secret: bytes, epoch: int, now: float | None = None) -> str:
    body = _b64(json.dumps({"e": epoch, "t": int(now or time.time())}).encode())
    sig = _b64(hmac.new(secret, body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def check_token(secret: bytes, token: str, epoch: int, now: float | None = None) -> bool:
    try:
        body, sig = token.split(".")
        expected = _b64(hmac.new(secret, body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return False
        data = json.loads(_unb64(body))
    except (ValueError, json.JSONDecodeError):
        return False
    if data.get("e") != epoch:
        return False
    return (now or time.time()) - data.get("t", 0) < SESSION_DAYS * 86400


@dataclass
class RateLimiter:
    """同一来源连续失败 MAX_FAILURES 次后锁定 LOCK_SECONDS 秒。"""

    failures: dict[str, list[float]] = field(default_factory=dict)
    locked_until: dict[str, float] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def check(self, key: str, now: float | None = None) -> float:
        """返回还需等待的秒数，0 表示可以尝试。"""
        now = now or time.time()
        with self.lock:
            until = self.locked_until.get(key, 0)
            return max(0.0, until - now)

    def fail(self, key: str, now: float | None = None) -> None:
        now = now or time.time()
        with self.lock:
            recent = [t for t in self.failures.get(key, []) if now - t < LOCK_SECONDS] + [now]
            self.failures[key] = recent
            if len(recent) >= MAX_FAILURES:
                self.locked_until[key] = now + LOCK_SECONDS
                self.failures[key] = []

    def succeed(self, key: str) -> None:
        with self.lock:
            self.failures.pop(key, None)
            self.locked_until.pop(key, None)


def require_login(request: Request) -> None:
    ctx = request.app.state.ctx
    token = request.cookies.get(COOKIE_NAME, "")
    if not token or not check_token(ctx.secret_key, token, ctx.session_epoch()):
        raise HTTPException(status_code=401, detail="请先登录")
