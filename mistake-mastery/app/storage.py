"""数据目录里的文件：进 git 的图片在 files/，本地缓存和 PDF 在 .local/。"""

import shutil
from datetime import datetime
from pathlib import Path


class Storage:
    def __init__(self, data_dir: Path):
        self.root = data_dir.resolve()
        self.local = self.root / ".local"
        self.cache = self.local / "cache"
        self.pdf = self.local / "pdf"
        for d in (self.cache, self.pdf):
            d.mkdir(parents=True, exist_ok=True)

    # 进 git 的文件，路径相对数据仓库根目录（存在数据库里的就是这个相对路径）。
    def page_dir(self, page_id: str, when: datetime | None = None) -> str:
        when = when or datetime.now()
        return f"files/pages/{when:%Y/%m}/{page_id}"

    def bank_dir(self, paper_id: str) -> str:
        return f"files/bank/{paper_id}"

    def delete_tree(self, rel: str) -> None:
        """删除数据仓库里的一个目录（git 历史里仍然能找回）。"""
        p = self.abspath(rel)
        if p != self.root and p.is_dir():
            shutil.rmtree(p)

    def abspath(self, rel: str) -> Path:
        """把相对路径解析成绝对路径，并确保不会跳出数据目录。"""
        p = (self.root / rel).resolve()
        if p != self.root and self.root not in p.parents:
            raise ValueError(f"path escapes data dir: {rel}")
        return p

    def write(self, rel: str, data: bytes) -> str:
        p = self.abspath(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(p)
        return rel

    def read(self, rel: str) -> bytes:
        return self.abspath(rel).read_bytes()

    def exists(self, rel: str) -> bool:
        return self.abspath(rel).exists()

    def is_shareable(self, rel: str) -> bool:
        """可以通过 /api/files 读取的文件：files/ 下的图片，或 .local/ 下的 PDF 和缓存。"""
        p = self.abspath(rel)
        return any(base in p.parents for base in (self.root / "files", self.pdf, self.cache))
