"""端到端：登录 → 上传 → 确认 → 错题本 → 打印 → 回填 → 同步到"GitHub" → 在"新电脑"上恢复。"""

import subprocess
from pathlib import Path

import fitz  # pymupdf
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.sync import export_all, import_all
from tests.conftest import PASSWORD, fake_llm, make_data_repo, synthetic_page


def chromium_ok(path: str) -> bool:
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as p:
            p.chromium.launch(**({"executable_path": path} if path else {})).close()
        return True
    except Exception:  # noqa: BLE001
        return False


def _upload(c: TestClient, student_id: str) -> str:
    r = c.post("/api/captures", data={"student_id": student_id, "subject": "math", "mode": "page",
                                       "source_kind": "monthly"},
               files=[("files", ("p1.jpg", synthetic_page(), "image/jpeg"))])
    assert r.status_code == 200, r.text
    job = c.get(f"/api/jobs/{r.json()['job_id']}").json()
    assert job["status"] == "done", job
    return r.json()["document_id"]


def test_requires_login(client):
    assert client.get("/api/students").status_code == 401
    assert client.get("/api/health").status_code == 200


def test_login_rate_limit(client):
    for _ in range(5):
        assert client.post("/api/login", json={"password": "wrong"}).status_code == 401
    assert client.post("/api/login", json={"password": PASSWORD}).status_code == 429


def test_logout_all_invalidates_sessions(logged_in):
    assert logged_in.get("/api/students").status_code == 200
    assert logged_in.post("/api/logout-all").status_code == 200
    logged_in.cookies.clear()
    assert logged_in.get("/api/students").status_code == 401


def test_full_flow_and_restore(logged_in, tmp_path, make_settings):
    c = logged_in
    ctx = c.app_ctx
    st = c.post("/api/students", json={"name": "小测", "district": "haidian"}).json()
    doc_id = _upload(c, st["id"])

    doc = c.get(f"/api/documents/{doc_id}").json()
    assert doc["title"] == "测试卷 · 九年级数学"
    assert doc["pages"][0]["erase_status"] == "done"

    cand = c.get(f"/api/documents/{doc_id}/candidates").json()["items"]
    assert [i["number_label"] for i in cand] == ["1", "2", "3"]
    assert [i["preselected"] for i in cand] == [True, True, False]
    assert cand[0]["kp_codes"] == ["M.FUN.QUAD.GRAPH"]  # 不存在的编码被丢掉
    assert cand[0]["cause_suggestions"] == ["READING"]
    assert cand[1]["question"]["answer_source"] == "teacher"
    img = c.get(f"/api/instances/{cand[0]['instance_id']}/image?kind=erased")
    assert img.status_code == 200 and img.content[:3] == b"\xff\xd8\xff"

    r = c.post(f"/api/documents/{doc_id}/confirm", json={"items": [
        {"instance_id": cand[0]["instance_id"], "selected": True},
        {"instance_id": cand[1]["instance_id"], "selected": True, "error_causes": ["M_AUX"]},
        {"instance_id": cand[2]["instance_id"], "selected": False},
    ]}).json()
    assert r == {"created": 2, "merged": 0, "solving": 1}

    mistakes = c.get(f"/api/mistakes?student_id={st['id']}").json()
    assert len(mistakes) == 2 and {m["status"] for m in mistakes} == {"TO_REDO"}
    by_label = {m["number_label"]: m for m in mistakes}
    first = c.get(f"/api/mistakes/{by_label['1']['id']}").json()
    assert first["question"]["answer"] == {"final": "B"} and first["question"]["answer_source"] == "ai_unverified"
    assert by_label["2"]["error_causes"] == ["M_AUX"]

    # 再录入同一张卷子：同一道题合并，错误次数 +1
    doc2 = _upload(c, st["id"])
    cand2 = c.get(f"/api/documents/{doc2}/candidates").json()["items"]
    r2 = c.post(f"/api/documents/{doc2}/confirm", json={"items": [
        {"instance_id": cand2[0]["instance_id"], "selected": True}]}).json()
    assert r2["merged"] == 1 and r2["created"] == 0
    assert c.get(f"/api/mistakes/{by_label['1']['id']}").json()["wrong_count"] == 2

    if chromium_ok(ctx.settings.chromium_path):
        pj = c.post("/api/print-jobs", json={"student_id": st["id"], "template": "redo_sheet",
                                             "mistake_ids": [by_label["1"]["id"], by_label["2"]["id"]],
                                             "layout": {"with_key": True}}).json()
        job = c.get(f"/api/print-jobs/{pj['print_job_id']}").json()
        assert job["status"] == "ready", job
        pdf = c.get(f"/api/print-jobs/{pj['print_job_id']}/pdf")
        assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
        with fitz.open(stream=pdf.content, filetype="pdf") as d:
            assert d.page_count == job["page_count"] + 1  # 题目页 + 答案页
            text = "".join(p.get_text() for p in d)
            assert "错题重做单" in text and "AI 生成 · 待核" in text
            assert abs(d[0].rect.width - 595.3) < 1  # A4
        assert all(it["page_no"] for it in job["items"])

        restore = c.post("/api/print-jobs", json={"student_id": st["id"], "template": "page_restore",
                                                  "document_id": doc_id}).json()
        rj = c.get(f"/api/print-jobs/{restore['print_job_id']}").json()
        assert rj["status"] == "ready" and rj["page_count"] == 1

        res = c.post(f"/api/print-jobs/{pj['print_job_id']}/results",
                     json={"results": [{"seq": 1, "result": "correct"}, {"seq": 2, "result": "wrong"}]}).json()
        assert res["recorded"] == 2
        assert [i["status"] for i in res["items"]] == ["TO_VARIANT", "TO_TUTOR"]
    else:
        pytest.skip("没有可用的 Chromium，跳过 PDF 部分")

    # 同步到"GitHub"（本地裸仓库）
    s = c.post("/api/sync").json()
    assert s["pushed"] and s["status"]["unpushed_commits"] == 0
    data = ctx.settings.data_dir
    assert (data / "tables" / "mistakes.jsonl").exists()
    assert list((data / "files" / "pages").rglob("erased.png"))
    tracked = subprocess.run(["git", "ls-files"], cwd=data, capture_output=True, text=True).stdout
    assert ".local" not in tracked and "app.db" not in tracked

    # "新电脑"：clone 数据仓库后启动，自动从 JSONL 重建索引
    new_data, _ = make_data_repo(tmp_path, name="restored")
    app2 = create_app(make_settings(new_data), start_background=False)
    app2.state.ctx.llm.fake = fake_llm
    assert app2.state.ctx.restored["mistakes"] == 2
    with TestClient(app2) as c2:
        assert c2.post("/api/login", json={"password": PASSWORD}).status_code == 200
        again = c2.get(f"/api/mistakes?student_id={st['id']}").json()
        assert sorted((m["number_label"], m["status"], m["wrong_count"]) for m in again) == \
            sorted((m["number_label"], m["status"], m["wrong_count"]) for m in
                   c.get(f"/api/mistakes?student_id={st['id']}").json())
        assert c2.get(f"/api/instances/{cand[0]['instance_id']}/image?kind=erased").status_code == 200


def test_cross_page_question_merges_and_blank_is_flagged(logged_in):
    """拍两页：第 2 页开头是第 1 页最后一道题的选项（跨页），要接到那道题上；没作答没批改的题标 blank。"""
    c = logged_in
    calls = []

    def fake(task: str, messages: list[dict]):
        if task != "recognize":
            return fake_llm(task, messages)
        calls.append(task)
        if len(calls) == 1:
            return fake_llm(task, messages)
        return {"header": None, "questions": [
            {"number_label": "", "continued": True, "bbox": [60, 0, 940, 180], "question_type": "fill",
             "stem_md": "", "options": [{"key": "A", "md": "$\\sqrt{3}$"}, {"key": "B", "md": "$3$"}], "grading": "wrong",
             "student_answer": "B", "has_figure": True},
            {"number_label": "4", "bbox": [60, 200, 940, 600], "question_type": "solve",
             "stem_md": "解方程 $x^2=4$。", "grading": "none", "student_answer": None, "has_figure": False},
        ]}

    c.app_ctx.llm.fake = fake
    st = c.post("/api/students", json={"name": "小测"}).json()
    r = c.post("/api/captures", data={"student_id": st["id"], "subject": "math", "mode": "page", "source_kind": "monthly"},
               files=[("files", ("p1.jpg", synthetic_page(), "image/jpeg")), ("files", ("p2.jpg", synthetic_page(), "image/jpeg"))])
    assert r.status_code == 200, r.text
    assert c.get(f"/api/jobs/{r.json()['job_id']}").json()["status"] == "done"
    cand = c.get(f"/api/documents/{r.json()['document_id']}/candidates").json()["items"]
    assert [i["number_label"] for i in cand] == ["1", "2", "3", "4"]  # 后半段没有成为第 5 道
    third = cand[2]
    assert third["pages"] == [1, 2] and third["question"]["options"] == [{"key": "A", "md": "$\\sqrt{3}$"}, {"key": "B", "md": "$3$"}]
    assert third["grading"] == "wrong" and third["preselected"] and third["student_answer"] == "B"
    assert not third["blank"] and cand[3]["blank"] and not cand[3]["preselected"]
    # 截图把两页的两段竖着拼起来，比只截第 1 页的高
    import io
    from PIL import Image
    full = Image.open(io.BytesIO(c.get(f"/api/instances/{third['instance_id']}/image?kind=erased&max_side=3000").content))
    one = Image.open(io.BytesIO(c.get(f"/api/instances/{cand[1]['instance_id']}/image?kind=erased&max_side=3000").content))
    assert full.height > one.height


def test_ocr_anchors_question_boxes_and_reversed_pages_are_reordered(logged_in, monkeypatch):
    """模型给的框不准：有 OCR 文字层时，每道题从题号那一行开始、到下一道题的题号之前；
    照片倒着传（第 1 张是后面的题）时按题号把页码倒过来。"""
    from app.adapters.pdf import Layout, Line
    from app.services import capture

    c = logged_in
    c.app_ctx.settings = c.app_ctx.settings.model_copy(update={"ocr_enabled": True})
    # 合成页上三道题的题号行在 y=120/540/960（纸张 1414 高）→ 归一化约 85/382/679；模型的框故意给偏
    rows = [(85, "1. Question text line for test number 1"), (382, "2. Question text line for test number 2"),
            (679, "3. Question text line for test number 3"), (960, "第 1 页 / 共 2 页")]
    monkeypatch.setattr(capture.ocr, "page_layout", lambda img: Layout(
        lines=[Line(y0=y, y1=y + 12, x0=60, x1=700, text=t) for y, t in rows]))
    calls = []

    def fake(task: str, messages: list[dict]):
        if task != "recognize":
            return fake_llm(task, messages)
        calls.append(task)
        base = fake_llm(task, messages)
        for q in base["questions"]:
            q["bbox"] = [q["bbox"][0], q["bbox"][1] + 120, q["bbox"][2], q["bbox"][3] + 120]  # 偏下 12%
        if len(calls) == 1:  # 第一张照片却是后面的题：4、5、6
            for q in base["questions"]:
                q["number_label"] = str(int(q["number_label"]) + 3)
        return base

    c.app_ctx.llm.fake = fake
    st = c.post("/api/students", json={"name": "小测"}).json()
    r = c.post("/api/captures", data={"student_id": st["id"], "subject": "math", "mode": "page", "source_kind": "monthly"},
               files=[("files", ("p1.jpg", synthetic_page(), "image/jpeg")), ("files", ("p2.jpg", synthetic_page(), "image/jpeg"))])
    assert c.get(f"/api/jobs/{r.json()['job_id']}").json()["status"] == "done"
    cand = c.get(f"/api/documents/{r.json()['document_id']}/candidates").json()["items"]
    assert [i["number_label"] for i in cand] == ["1", "2", "3", "4", "5", "6"]  # 页码倒过来了
    assert [i["page_no"] for i in cand] == [1, 1, 1, 2, 2, 2]
    h = c.get(f"/api/documents/{r.json()['document_id']}").json()["pages"][0]["ch"]
    tops = [i["bbox"][1] / h * 1000 for i in cand[:3]]
    assert all(abs(t - (y - 6)) < 3 for t, y in zip(tops, (85, 382, 679)))  # 题号行往上留 2 毫米
    assert cand[0]["bbox"][3] / h * 1000 < 382 and cand[2]["bbox"][3] / h * 1000 <= 960 - 6 + 0.5  # 到下一题、页脚之前


def test_export_is_deterministic_and_roundtrips(logged_in, tmp_path, make_settings):
    c = logged_in
    st = c.post("/api/students", json={"name": "小测"}).json()
    doc_id = _upload(c, st["id"])
    cand = c.get(f"/api/documents/{doc_id}/candidates").json()["items"]
    c.post(f"/api/documents/{doc_id}/confirm",
           json={"items": [{"instance_id": i["instance_id"], "selected": True} for i in cand]})
    ctx = c.app_ctx
    data = ctx.settings.data_dir
    export_all(ctx.db, data)
    assert export_all(ctx.db, data) == []  # 再导出一次没有任何变化

    snapshot = {p.relative_to(data): p.read_bytes() for p in (data / "tables").rglob("*.jsonl")}
    assert snapshot, "应该导出了表数据"
    text = (data / "tables" / "questions.jsonl").read_text(encoding="utf-8")
    assert "二次函数" in text  # 中文不转义，GitHub 网页上能直接看

    # 导入到一个全新的数据库，再导出，逐字节一致
    other = tmp_path / "other"
    other.mkdir()
    for rel, content in snapshot.items():
        (other / rel).parent.mkdir(parents=True, exist_ok=True)
        (other / rel).write_bytes(content)
    from app.db import Database
    db2 = Database(other / ".local" / "app.db")
    import_all(db2, other)
    for rel in snapshot:
        (other / rel).unlink()
    export_all(db2, other)
    again = {p.relative_to(other): p.read_bytes() for p in (other / "tables").rglob("*.jsonl")}
    assert again == snapshot


def test_kp_mastery_and_priority_not_exported(logged_in):
    ctx = logged_in.app_ctx
    export_all(ctx.db, ctx.settings.data_dir)
    tables = Path(ctx.settings.data_dir / "tables")
    assert not (tables / "kp_mastery.jsonl").exists()
    assert not (tables / "jobs.jsonl").exists()
    assert not (tables / "ai_calls.jsonl").exists()
