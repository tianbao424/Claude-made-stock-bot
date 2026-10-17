"""进程内任务队列：任务记在 jobs 表里，进程重启后把未完成的任务重新入队。"""

import logging
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, Callable

from app.db import Database
from app.ids import now_iso
from app.models import Job

if TYPE_CHECKING:
    from app.context import AppContext

log = logging.getLogger(__name__)


class JobHandle:
    def __init__(self, db: Database, job_id: str):
        self.db = db
        self.id = job_id

    def progress(self, stage: str, pct: int) -> None:
        with self.db.session() as s:
            job = s.get(Job, self.id)
            if job:
                job.progress = {"stage": stage, "pct": pct}
                job.updated_at = now_iso()


Handler = Callable[["AppContext", JobHandle, dict], dict | None]


class JobRunner:
    def __init__(self, db: Database, *, inline: bool = False, workers: int = 2):
        self.db = db
        self.inline = inline
        self.handlers: dict[str, Handler] = {}
        self.ctx: "AppContext | None" = None
        self._pool = None if inline else ThreadPoolExecutor(workers, thread_name_prefix="job")

    def register(self, kind: str, handler: Handler) -> None:
        self.handlers[kind] = handler

    def submit(self, kind: str, payload: dict[str, Any]) -> str:
        if kind not in self.handlers:
            raise KeyError(f"no handler for job kind {kind!r}")
        with self.db.session() as s:
            job = Job(kind=kind, payload=payload, status="queued", progress={"stage": "排队中", "pct": 0})
            s.add(job)
            s.flush()
            job_id = job.id
        self._dispatch(job_id)
        return job_id

    def _dispatch(self, job_id: str) -> None:
        if self.inline:
            self._run(job_id)
        else:
            assert self._pool is not None
            self._pool.submit(self._run, job_id)

    def _run(self, job_id: str) -> None:
        with self.db.session() as s:
            job = s.get(Job, job_id)
            if job is None or job.status in ("done", "failed"):
                return
            job.status = "running"
            job.attempts += 1
            job.updated_at = now_iso()
            kind, payload = job.kind, dict(job.payload)
        try:
            result = self.handlers[kind](self.ctx, JobHandle(self.db, job_id), payload)
        except Exception as exc:  # noqa: BLE001 —— 任务失败要记下原因，不能让线程静默退出
            log.error("job %s (%s) failed:\n%s", job_id, kind, traceback.format_exc())
            with self.db.session() as s:
                job = s.get(Job, job_id)
                job.status = "failed"
                job.error = str(exc)[:2000] or exc.__class__.__name__
                job.updated_at = now_iso()
            return
        with self.db.session() as s:
            job = s.get(Job, job_id)
            job.status = "done"
            job.result = result or {}
            job.progress = {"stage": "完成", "pct": 100}
            job.updated_at = now_iso()

    def resume(self) -> int:
        """把上次进程退出时没跑完的任务重新入队。"""
        with self.db.session() as s:
            ids = [
                j.id
                for j in s.query(Job).filter(Job.status.in_(("queued", "running"))).order_by(Job.created_at)
            ]
        for job_id in ids:
            with self.db.session() as s:
                s.get(Job, job_id).status = "queued"
            self._dispatch(job_id)
        return len(ids)

    def shutdown(self) -> None:
        if self._pool:
            self._pool.shutdown(wait=False, cancel_futures=True)
