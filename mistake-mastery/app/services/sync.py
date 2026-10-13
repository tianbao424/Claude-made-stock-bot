"""同步到 GitHub 私有数据仓库（见 docs/03 §5、docs/04 §6）。

- 导出：每张需同步的表写成 tables/<表名>.jsonl，按主键排序、键有序、不转义中文，
  同样的数据导出两次逐字节相同；作答记录按月分文件。
- 提交：最后一次改动后等 debounce 秒再 git commit + push；推送失败指数退避重试。
- 重建：清空 SQLite，从 JSONL 读回（rebuild_index 工具调用 import_all）。
"""

import json
import logging
import subprocess
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import inspect

from app.config import Settings
from app.db import Database
from app.ids import now_iso
from app.models import SYNCED_MODELS, Base

log = logging.getLogger(__name__)

TABLES_DIR = "tables"
FALLBACK_INTERVAL = 30 * 60
MAX_BACKOFF = 30 * 60


def _columns(model: type[Base]) -> list[str]:
    return [c.key for c in inspect(model).columns if c.key not in model.__local_cols__]


def _pk(model: type[Base]) -> list:
    return list(inspect(model).primary_key)


def _line(row: Base, cols: list[str]) -> str:
    data = {c: getattr(row, c) for c in cols}
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def _sorted_models() -> list[type[Base]]:
    """按外键依赖排序，导入时先插被引用的表。"""
    order = {t.name: i for i, t in enumerate(Base.metadata.sorted_tables)}
    return sorted(SYNCED_MODELS, key=lambda m: order[m.__tablename__])


def _write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)
    return True


def export_all(db: Database, data_dir: Path) -> list[str]:
    """把需同步的表导出成 JSONL，返回内容有变化的文件（相对路径）。"""
    changed: list[str] = []
    tables_dir = data_dir / TABLES_DIR
    with db.session() as s:
        for model in _sorted_models():
            cols = _columns(model)
            rows = s.query(model).order_by(*_pk(model)).all()
            if model.__sync__ == "monthly":
                by_month: dict[str, list[str]] = defaultdict(list)
                for r in rows:
                    by_month[r.created_at[:7]].append(_line(r, cols))
                folder = tables_dir / model.__tablename__
                wanted = {f"{m}.jsonl" for m in by_month}
                for month, lines in by_month.items():
                    path = folder / f"{month}.jsonl"
                    if _write_if_changed(path, "\n".join(lines) + "\n"):
                        changed.append(str(path.relative_to(data_dir)))
                if folder.exists():
                    for stale in folder.glob("*.jsonl"):
                        if stale.name not in wanted:
                            stale.unlink()
                            changed.append(str(stale.relative_to(data_dir)))
            else:
                path = tables_dir / f"{model.__tablename__}.jsonl"
                content = "".join(_line(r, cols) + "\n" for r in rows)
                if _write_if_changed(path, content):
                    changed.append(str(path.relative_to(data_dir)))
    return changed


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            out.append(json.loads(raw))
    return out


def import_all(db: Database, data_dir: Path) -> dict[str, int]:
    """从 JSONL 读回到（空的）SQLite。未知字段忽略，缺少的字段用默认值，方便表结构演进。"""
    counts: dict[str, int] = {}
    tables_dir = data_dir / TABLES_DIR
    with db.session() as s:
        for model in _sorted_models():
            cols = set(_columns(model))
            if model.__sync__ == "monthly":
                files = sorted((tables_dir / model.__tablename__).glob("*.jsonl"))
            else:
                f = tables_dir / f"{model.__tablename__}.jsonl"
                files = [f] if f.exists() else []
            n = 0
            for f in files:
                for data in _read_jsonl(f):
                    s.add(model(**{k: v for k, v in data.items() if k in cols}))
                    n += 1
            s.flush()
            counts[model.__tablename__] = n
    return counts


class Git:
    def __init__(self, repo: Path):
        self.repo = repo

    def run(self, *args: str, check: bool = True, timeout: int = 120) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-c", "user.name=学透", "-c", "user.email=xuetou@localhost", "-C", str(self.repo), *args],
            capture_output=True, text=True, timeout=timeout, check=check)

    def is_repo(self) -> bool:
        return (self.repo / ".git").exists()

    def has_remote(self) -> bool:
        return bool(self.run("remote", check=False).stdout.strip())

    def commit_all(self, message: str) -> bool:
        self.run("add", "-A")
        if self.run("diff", "--cached", "--quiet", check=False).returncode == 0:
            return False
        self.run("commit", "-q", "-m", message)
        return True

    def unpushed(self) -> int:
        r = self.run("rev-list", "--count", "@{u}..HEAD", check=False)
        if r.returncode != 0:  # 还没有上游分支
            r2 = self.run("rev-list", "--count", "HEAD", check=False)
            return int(r2.stdout.strip() or 0) if r2.returncode == 0 else 0
        return int(r.stdout.strip() or 0)

    def push(self) -> None:
        r = self.run("push", "-u", "origin", "HEAD", check=False, timeout=180)
        if r.returncode != 0:
            raise RuntimeError((r.stderr or r.stdout).strip()[-500:])


class SyncManager:
    def __init__(self, settings: Settings, db: Database):
        self.settings = settings
        self.db = db
        self.data_dir = settings.data_dir
        self.git = Git(settings.data_dir)
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._dirty = False
        self._last_change = 0.0
        self._last_sync_try = 0.0
        self.last_synced_at: str | None = None
        self.last_pushed_at: str | None = None
        self.last_error: str | None = None
        self._backoff = 60.0
        self._next_push_try = 0.0
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------ 状态

    def enabled(self) -> bool:
        return self.settings.sync_enabled and self.git.is_repo()

    def status(self) -> dict:
        return {
            "enabled": self.enabled(),
            "is_git_repo": self.git.is_repo(),
            "has_remote": self.git.is_repo() and self.git.has_remote(),
            "dirty": self._dirty,
            "unpushed_commits": self.git.unpushed() if self.git.is_repo() else 0,
            "last_synced_at": self.last_synced_at,
            "last_pushed_at": self.last_pushed_at,
            "last_error": self.last_error,
        }

    # ------------------------------------------------------------ 触发

    def touch(self) -> None:
        self._dirty = True
        self._last_change = time.time()
        self._wake.set()

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._loop, name="sync", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._dirty and self.enabled():
            try:
                self.sync_now()
            except Exception:  # noqa: BLE001 —— 退出时尽力而为
                log.exception("final sync failed")

    def _loop(self) -> None:
        while not self._stop.is_set():
            timeout = 30.0
            if self._dirty:  # 有改动时，睡到防抖时间结束为止
                remaining = self.settings.sync_debounce_seconds - (time.time() - self._last_change)
                timeout = max(0.5, min(timeout, remaining))
            self._wake.wait(timeout=timeout)
            self._wake.clear()
            if self._stop.is_set() or not self.enabled():
                continue
            now = time.time()
            due_debounce = self._dirty and now - self._last_change >= self.settings.sync_debounce_seconds
            due_fallback = self._dirty and now - self._last_sync_try >= FALLBACK_INTERVAL
            due_push = self.last_error is not None and now >= self._next_push_try
            if due_debounce or due_fallback or due_push:
                try:
                    self.sync_now()
                except Exception:  # noqa: BLE001
                    log.exception("sync failed")

    # ------------------------------------------------------------ 执行

    def sync_now(self, push: bool | None = None) -> dict:
        """导出 → 提交 → 推送。返回本次的结果摘要。"""
        push = self.settings.sync_push if push is None else push
        with self._lock:
            self._last_sync_try = time.time()
            self._dirty = False
            changed = export_all(self.db, self.data_dir)
            committed = False
            if self.git.is_repo():
                committed = self.git.commit_all(f"学透自动同步 {now_iso()[:16].replace('T', ' ')}")
            self.last_synced_at = now_iso()
            pushed = False
            if push and self.git.is_repo() and self.git.has_remote() and self.git.unpushed() > 0:
                try:
                    self.git.push()
                    pushed = True
                    self.last_pushed_at = now_iso()
                    self.last_error = None
                    self._backoff = 60.0
                except RuntimeError as exc:
                    self.last_error = f"推送失败（提交已保存在本地，会自动重试）：{exc}"
                    self._next_push_try = time.time() + self._backoff
                    self._backoff = min(self._backoff * 2, MAX_BACKOFF)
            return {"changed_files": changed, "committed": committed, "pushed": pushed, "error": self.last_error}
