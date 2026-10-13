"""SQLite 工作数据库。它只是索引：随时可以从数据仓库的 JSONL 重建（app.tools.rebuild_index）。"""

from contextlib import contextmanager
from itertools import chain
from pathlib import Path
from typing import Callable, Iterator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base

DATA_REPO_GITIGNORE = ".local/\n.DS_Store\n"


def ensure_data_dir(data_dir: Path) -> None:
    """数据目录就是私有数据仓库的克隆；.local/ 放本地专用的东西，不进 git。"""
    (data_dir / ".local").mkdir(parents=True, exist_ok=True)
    gitignore = data_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(DATA_REPO_GITIGNORE, encoding="utf-8")


def make_engine(db_path: Path) -> Engine:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )

    @event.listens_for(engine, "connect")
    def _pragmas(dbapi_conn, _record):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.close()

    return engine


def init_schema(engine: Engine) -> list[str]:
    Base.metadata.create_all(engine)
    return add_missing_columns(engine)


def add_missing_columns(engine: Engine) -> list[str]:
    """升级后给已有的表补上新加的列（新列一律允许为空）。其他结构变化靠从数据仓库重建索引。"""
    insp = inspect(engine)
    added: list[str] = []
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            have = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name not in have:
                    ddl = col.type.compile(engine.dialect)
                    conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {ddl}'))
                    added.append(f"{table.name}.{col.name}")
    return added


class Database:
    def __init__(self, db_path: Path):
        self.engine = make_engine(db_path)
        init_schema(self.engine)
        self._factory = sessionmaker(self.engine, expire_on_commit=False)
        # 需要同步到 GitHub 的表有改动并提交后调用（由同步服务挂上）。
        self.on_change: Callable[[], None] | None = None

        @event.listens_for(self._factory, "before_flush")
        def _mark(session, _ctx, _instances):  # noqa: ANN001
            for obj in chain(session.new, session.dirty, session.deleted):
                if getattr(type(obj), "__sync__", None):
                    session.info["synced_dirty"] = True
                    return

        @event.listens_for(self._factory, "after_commit")
        def _notify(session):  # noqa: ANN001
            if session.info.pop("synced_dirty", False) and self.on_change:
                self.on_change()

    @contextmanager
    def session(self) -> Iterator[Session]:
        s = self._factory()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    def dispose(self) -> None:
        self.engine.dispose()
