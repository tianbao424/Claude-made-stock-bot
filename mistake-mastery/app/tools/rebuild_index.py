"""从数据仓库的 JSONL 重建 SQLite 索引：uv run python -m app.tools.rebuild_index

适用于：数据库损坏、在 GitHub 网页上手动改过数据文件、升级后表结构有变化。
启动程序时如果发现数据库是空的，也会自动做同样的事。
"""

from app.config import get_settings
from app.db import Database, ensure_data_dir
from app.services.sync import import_all


def main() -> None:
    s = get_settings()
    ensure_data_dir(s.data_dir)
    if s.db_path.exists():
        backup = s.db_path.with_suffix(".db.bak")
        s.db_path.replace(backup)
        for extra in ("-wal", "-shm"):
            s.db_path.with_name(s.db_path.name + extra).unlink(missing_ok=True)
        print(f"旧数据库已备份到 {backup}")
    db = Database(s.db_path)
    counts = import_all(db, s.data_dir)
    db.dispose()
    print("重建完成：", ", ".join(f"{k} {v}" for k, v in counts.items() if v))


if __name__ == "__main__":
    main()
