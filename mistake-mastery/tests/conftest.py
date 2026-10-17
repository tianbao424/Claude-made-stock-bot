"""测试夹具：临时数据仓库（带一个裸仓库当作 GitHub）、假的大模型、合成的试卷照片。"""

import io
import os
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.config import Settings
from app.main import create_app

PASSWORD = "test-family-pass"
CHROMIUM = os.environ.get("XT_CHROMIUM_PATH", "")


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout


def make_data_repo(tmp: Path, name: str = "data") -> tuple[Path, Path]:
    """新建一个"私有数据仓库"的克隆，远端是本地的裸仓库。"""
    remote = tmp / "remote.git"
    if not remote.exists():
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    data = tmp / name
    subprocess.run(["git", "clone", "-q", str(remote), str(data)], check=True, capture_output=True)
    return data, remote


def fake_llm(task: str, messages: list[dict]):
    """按任务返回固定结构的结果：一页切成 3 道题，前两道被老师判错。"""
    if task == "recognize":
        return {"header": "测试卷 · 九年级数学", "questions": [
            {"number_label": "1", "bbox": [60, 80, 940, 360], "question_type": "choice_single",
             "stem_md": "已知二次函数 $y=x^2-2x$，下列说法正确的是", "options": [{"key": "A", "md": "开口向下"}],
             "grading": "wrong", "student_answer": "A", "teacher_answer": None, "has_figure": False},
            {"number_label": "2", "bbox": [60, 380, 940, 640], "question_type": "solve",
             "stem_md": "如图，在 $\\triangle ABC$ 中，$AB=AC$，求证 $BD=CE$。", "grading": "partial",
             "score_text": "3/6", "teacher_answer": "略", "has_figure": True},
            {"number_label": "3", "bbox": [60, 660, 940, 940], "question_type": "fill",
             "stem_md": "计算 $\\sqrt{12}-\\sqrt{3}=$____", "grading": "right"},
        ]}
    if task == "classify":
        import json as _json
        text = messages[-1]["content"]
        rows = _json.loads(text.split("【题目】")[1].split("对每道题输出")[0])
        return {"items": [{"id": r["id"], "kp_codes": ["M.FUN.QUAD.GRAPH", "NOT.A.CODE"],
                           "bj_slot": "math.q8.choice_final", "difficulty": 3, "error_causes": ["READING"]}
                          for r in rows]}
    if task == "solve":
        return {"final_answer": "B", "solution_md": "对称轴 $x=1$……", "confidence": 0.8}
    raise AssertionError(f"unexpected task {task}")


def synthetic_page(width: int = 1200, height: int = 1600) -> bytes:
    """深色桌面上的一张白纸：黑色印刷字 + 红笔批改，用于测试矫正、擦除和打印。"""
    canvas = Image.new("RGB", (width, height), (60, 50, 45))
    paper = Image.new("RGB", (1000, 1414), "white")
    d = ImageDraw.Draw(paper)
    for i in range(3):
        top = 120 + i * 420
        d.text((60, top), f"{i + 1}. Question text line for test number {i + 1}", fill="black")
        for j in range(1, 5):
            d.line([(60, top + j * 40), (900, top + j * 40)], fill=(30, 30, 30), width=2)
        d.line([(700, top + 60), (850, top + 200)], fill=(220, 20, 20), width=8)  # 红笔 ✗
    canvas.paste(paper, (100, 90))
    buf = io.BytesIO()
    canvas.save(buf, "JPEG", quality=92)
    return buf.getvalue()


@pytest.fixture
def make_settings(tmp_path):
    def _make(data_dir: Path, **kw) -> Settings:
        return Settings(_env_file=None, data_dir=data_dir, family_password=PASSWORD, jobs_inline=True,
                        eraser="local_color", ocr_enabled=False, sync_debounce_seconds=3600, chromium_path=CHROMIUM, **kw)
    return _make


@pytest.fixture
def client(tmp_path, make_settings):
    data, _remote = make_data_repo(tmp_path)
    app = create_app(make_settings(data), start_background=False)
    app.state.ctx.llm.fake = fake_llm
    with TestClient(app) as c:
        c.app_ctx = app.state.ctx
        yield c


@pytest.fixture
def logged_in(client):
    r = client.post("/api/login", json={"password": PASSWORD})
    assert r.status_code == 200, r.text
    return client
