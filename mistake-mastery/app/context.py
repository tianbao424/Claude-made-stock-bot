"""应用上下文：把配置、数据库、存储、AI 客户端、任务队列和同步服务装在一起。"""

import json
import logging
from typing import Any

from sqlalchemy import delete

from app import curriculum
from app.adapters.eraser import Eraser, make_eraser
from app.adapters.llm import LLMClient
from app.auth import RateLimiter, load_secret_key
from app.config import Settings
from app.db import Database, ensure_data_dir
from app.jobs import JobRunner
from app.models import SYNCED_MODELS, AppSetting, KnowledgePoint
from app.services.sync import TABLES_DIR, SyncManager, import_all
from app.storage import Storage

log = logging.getLogger(__name__)

SETTINGS_FILE = "settings.json"


class AppContext:
    def __init__(self, settings: Settings):
        self.settings = settings
        ensure_data_dir(settings.data_dir)
        self.storage = Storage(settings.data_dir)
        self.db = Database(settings.db_path)
        self.curriculum = curriculum.load()
        self._load_knowledge_points()
        self.app_settings: dict[str, Any] = self._read_app_settings()
        self.secret_key = load_secret_key(settings.local_dir)
        self.rate_limiter = RateLimiter()
        self.llm = LLMClient(settings, self.db, self.storage.cache, models=self.app_settings.get("models"))
        self.jobs = JobRunner(self.db, inline=settings.jobs_inline)
        self.jobs.ctx = self
        self.sync = SyncManager(settings, self.db)
        self._eraser_override: Eraser | None = None
        self.restored = self._restore_if_empty()
        self.db.on_change = self.sync.touch

    # ------------------------------------------------------------ 启动

    def _load_knowledge_points(self) -> None:
        with self.db.session() as s:
            s.execute(delete(KnowledgePoint))
            for kp in self.curriculum.kps.values():
                s.add(KnowledgePoint(code=kp.code, subject=kp.subject, name=kp.name, parent_code=kp.parent_code,
                                     level=kp.level, bj_weight=kp.bj_weight))

    def _restore_if_empty(self) -> dict[str, int] | None:
        """换了电脑、刚 clone 下数据仓库时：SQLite 是空的而 tables/ 里有数据，自动重建索引。"""
        if not (self.settings.data_dir / TABLES_DIR).exists():
            return None
        with self.db.session() as s:
            if any(s.query(m).first() is not None for m in SYNCED_MODELS):
                return None
        counts = import_all(self.db, self.settings.data_dir)
        log.info("从数据仓库重建了索引：%s", counts)
        return counts

    def _read_app_settings(self) -> dict[str, Any]:
        path = self.settings.data_dir / SETTINGS_FILE
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def save_app_settings(self, patch: dict[str, Any]) -> dict[str, Any]:
        """非敏感设置写进数据仓库的 settings.json（会同步到 GitHub）。"""
        self.app_settings.update(patch)
        path = self.settings.data_dir / SETTINGS_FILE
        path.write_text(json.dumps(self.app_settings, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                        encoding="utf-8")
        if "models" in patch:
            self.llm.models.update(patch["models"] or {})
        self.sync.touch()
        return self.app_settings

    # ------------------------------------------------------------ 运行时

    def eraser(self) -> Eraser:
        if self._eraser_override is not None:
            return self._eraser_override
        return make_eraser(self.settings, self.app_settings.get("eraser"))

    def session_epoch(self) -> int:
        with self.db.session() as s:
            row = s.get(AppSetting, "session_epoch")
            return int(row.value) if row else 0

    def bump_session_epoch(self) -> int:
        with self.db.session() as s:
            row = s.get(AppSetting, "session_epoch")
            if row is None:
                row = AppSetting(key="session_epoch", value=0)
                s.add(row)
            row.value = int(row.value) + 1
            return row.value

    def start(self) -> None:
        resumed = self.jobs.resume()
        if resumed:
            log.info("恢复了 %d 个未完成的任务", resumed)
        self.sync.start()

    def stop(self) -> None:
        self.sync.stop()
        self.jobs.shutdown()
        self.db.dispose()
