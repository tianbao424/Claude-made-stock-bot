"""题库：导入合成的真题 PDF（有文字层）→ 切题、跨页合并、按题号对答案、AI 核对；录入时匹配；取消匹配；删除。"""

import io
import json

import fitz  # pymupdf
import pytest

from app.adapters.llm import CostCapExceeded
from app.db import Database
from app.services import bank
from tests.conftest import fake_llm, synthetic_page

STEM1 = "已知二次函数 $y=x^2-2x$，下列说法正确的是（　）"
OPTS1 = [{"key": "A", "md": "图象开口向下"}, {"key": "B", "md": "对称轴是直线 $x=1$"},
         {"key": "C", "md": "顶点坐标是 $(1,1)$"}, {"key": "D", "md": "与 $y$ 轴交点为 $(0,2)$"}]
STEM2 = "如图，在 $\\triangle ABC$ 中，$AB=AC$，点 $D$、$E$ 在 $BC$ 上，且 $BD=CE$。"
STEM3 = "计算：$\\sqrt{12}-\\sqrt{3}=$______"


def make_pdf(pages: list[list[str]], landscape: bool = False) -> bytes:
    doc = fitz.open()
    for lines in pages:
        page = doc.new_page(width=842 if landscape else 595, height=595 if landscape else 842)
        for i, line in enumerate(lines):
            page.insert_text((60, 70 + i * 28), line, fontname="china-s", fontsize=12)
    return doc.tobytes()


PAPER = make_pdf([
    ["2025 北京市海淀区九年级第一次模拟 数学", "一、选择题",
     "1. 已知二次函数 y=x2-2x，下列说法正确的是", "A. 图象开口向下  B. 对称轴是直线 x=1",
     "2. 如图，在△ABC中，AB=AC，点D、E在BC上，且BD=CE。(1) 求证：AD=AE；"],
    ["(2) 若∠BAC=120°，BD=DE，求∠DAE 的度数。", "3. 计算：√12-√3=______"],
])
ANSWERS = make_pdf([["参考答案及评分标准", "1. B", "2. (1) 证△ABD≌△ACE(SAS) (2) 60°", "3. √3"]])


def bank_fake(task: str, messages: list[dict]):
    """按 PDF 文字层判断是哪一页，返回固定的识别结果；其他任务交给通用的假模型。"""
    if task == "bank":
        prompt = messages[-1]["content"][1]["text"]
        text = prompt.split("<<<")[1].split(">>>")[0] if "<<<" in prompt else ""  # 只看 PDF 文字层
        if "第一次模拟" in text:
            return {"page_kind": "questions", "header": "2025 海淀一模 · 数学", "questions": [
                {"number_label": "1", "continued": False, "bbox": [50, 80, 950, 400], "question_type": "choice_single",
                 "stem_md": STEM1, "options": OPTS1, "has_figure": False, "points": "2分"},
                {"number_label": "2", "continued": False, "bbox": [50, 420, 950, 1000], "question_type": "solve",
                 "stem_md": STEM2, "sub_questions": [{"no": "(1)", "md": "求证：$AD=AE$；"}], "has_figure": True},
            ], "answers": []}
        if "∠BAC=120°" in text:
            return {"page_kind": "questions", "header": None, "questions": [
                {"number_label": "", "continued": True, "bbox": [50, 0, 950, 200], "question_type": "solve",
                 "stem_md": "", "sub_questions": [{"no": "(2)", "md": "若 $\\angle BAC=120°$，求 $\\angle DAE$。"}]},
                {"number_label": "3", "continued": False, "bbox": [50, 220, 950, 500], "question_type": "fill",
                 "stem_md": STEM3},
            ], "answers": []}
        if "参考答案" in text:
            return {"page_kind": "answers", "header": None, "questions": [], "answers": [
                {"number_label": "1", "final_answer": "B", "solution_md": None},
                {"number_label": "2(1)", "final_answer": "(1) 见解析", "solution_md": "证 △ABD≌△ACE（SAS）……2 分"},
                {"number_label": "2(2)", "final_answer": "(2) $60°$", "solution_md": "……"},
                {"number_label": "3", "final_answer": "$\\sqrt{3}$", "solution_md": None},
                {"number_label": "4", "final_answer": "多出来的答案", "solution_md": None},
            ]}
        return {"page_kind": "other", "questions": [], "answers": []}
    if task == "solve":
        stem = json.dumps(messages, ensure_ascii=False)
        if "二次函数" in stem:
            return {"final_answer": "B", "solution_md": "……", "confidence": 0.9}
        if "sqrt{12}" in stem:
            return {"final_answer": "$2\\sqrt{3}$", "solution_md": "算错了", "confidence": 0.6}
        return {"final_answer": "(1) 证明见解析；(2) 60°", "solution_md": "……", "confidence": 0.7}
    return fake_llm(task, messages)


@pytest.fixture
def bc(logged_in):
    logged_in.app_ctx.llm.fake = bank_fake
    return logged_in


def _import(c, paper=PAPER, answers=ANSWERS, **form) -> dict:
    files = [("paper_files", ("paper.pdf", paper, "application/pdf"))]
    if answers:
        files.append(("answer_files", ("answer.pdf", answers, "application/pdf")))
    data = {"subject": "math", "year": "2025", "region": "haidian", "exam_kind": "yimo", **form}
    r = c.post("/api/bank/papers", data=data, files=files)
    assert r.status_code == 200, r.text
    job = c.get(f"/api/jobs/{r.json()['job_id']}").json()
    assert job["status"] == "done", job
    return c.get(f"/api/bank/papers/{r.json()['paper_id']}").json()


def test_import_paper_with_answers(bc):
    p = _import(bc)
    assert p["status"] == "ready"
    assert p["title"] == "2025 海淀一模 · 数学"  # 没填名称时用卷头
    assert [pg["kind"] for pg in p["pages"]] == ["questions", "questions", "answers"]
    qs = p["questions"]
    assert [q["number_label"] for q in qs] == ["1", "2", "3"]
    # 第 2 题跨页：两段位置，小问合并
    assert qs[1]["pages"] == [1, 2]
    assert [s["no"] for s in qs[1]["sub_questions"]] == ["(1)", "(2)"]
    # 按题号对上答案；小问的答案归到大题
    assert qs[0]["answer"] == {"final": "B"} and qs[0]["answer_source"] == "official"
    assert qs[1]["answer"]["final"] == "(1) 见解析；(2) $60°$"
    assert "SAS" in qs[1]["solution_md"]
    assert p["stats"]["unmatched_answers"] == ["4"]
    # 分类
    assert qs[0]["kp_codes"] == ["M.FUN.QUAD.GRAPH"] and qs[0]["difficulty"] == 3
    # AI 核对：第 1、2 题一致，第 3 题对不上，交给家长看
    assert qs[0]["verification"]["agree"] is True and not qs[0]["needs_review"]
    assert qs[2]["verification"]["ai_answer"] == "$2\\sqrt{3}$" and qs[2]["needs_review"]
    assert p["stats"]["to_review"] == 1 and p["stats"]["questions"] == 3 and p["stats"]["official"] == 3

    # 家长看过：官方答案没问题
    r = bc.patch(f"/api/bank/questions/{qs[2]['id']}", json={"reviewed": True}).json()
    assert not r["needs_review"]
    assert bc.get(f"/api/bank/papers/{p['id']}").json()["stats"]["to_review"] == 0

    # 截图：跨页的题拼成一张
    img = bc.get(f"/api/bank/questions/{qs[1]['id']}/image")
    assert img.status_code == 200 and img.headers["content-type"] == "image/jpeg"
    assert bc.get(f"/api/bank/papers/{p['id']}/pages/1/image").status_code == 200

    # 文件进了数据仓库
    ctx = bc.app_ctx
    assert (ctx.settings.data_dir / f"files/bank/{p['id']}/paper-1.pdf").exists()


def test_import_without_answers_uses_ai(bc):
    p = _import(bc, answers=None, title="海淀一模（无答案）")
    assert p["title"] == "海淀一模（无答案）"
    q1 = p["questions"][0]
    assert q1["answer_source"] == "ai_unverified" and q1["answer"]["final"] == "B"
    assert p["stats"]["ai_only"] == 3 and p["stats"]["to_review"] == 0


def test_verify_pauses_at_cost_cap_and_resumes(bc):
    def capped(task, messages):
        if task == "solve":
            raise CostCapExceeded("今天的 AI 费用已达到上限")
        return bank_fake(task, messages)

    bc.app_ctx.llm.fake = capped
    p = _import(bc)
    assert p["status"] == "ready"
    assert p["stats"]["verify_paused"] is True and p["stats"]["unchecked"] == 3

    bc.app_ctx.llm.fake = bank_fake
    job = bc.post(f"/api/bank/papers/{p['id']}/verify").json()["job_id"]
    assert bc.get(f"/api/jobs/{job}").json()["status"] == "done"
    stats = bc.get(f"/api/bank/papers/{p['id']}").json()["stats"]
    assert stats["verify_paused"] is False and stats["unchecked"] == 0 and stats["to_review"] == 1


def test_bad_upload(bc):
    r = bc.post("/api/bank/papers", data={"subject": "math"},
                files=[("paper_files", ("x.pdf", b"not a pdf or image", "application/pdf"))])
    assert r.status_code == 400 and "不是 PDF" in r.json()["detail"]


def _capture(c, student_id: str, recognize: dict) -> str:
    def fake(task, messages):
        return recognize if task == "recognize" else bank_fake(task, messages)

    c.app_ctx.llm.fake = fake
    r = c.post("/api/captures", data={"student_id": student_id, "subject": "math", "mode": "page"},
               files=[("files", ("p.jpg", synthetic_page(), "image/jpeg"))])
    assert r.status_code == 200, r.text
    assert c.get(f"/api/jobs/{r.json()['job_id']}").json()["status"] == "done"
    c.app_ctx.llm.fake = bank_fake
    return r.json()["document_id"]


# 拍照识别出来的同一道题：题号、空格、全角标点和 LaTeX 写法都不一样
PHOTO_Q1 = {"number_label": "1", "bbox": [60, 80, 940, 360], "question_type": "choice_single",
            "stem_md": "1．已知二次函数 $y = x^{2} - 2x$ ,下列说法正确的是( )",
            "options": [{"key": "A", "md": "图象开口向下"}, {"key": "B", "md": "对称轴是直线$x=1$"},
                        {"key": "C", "md": "顶点坐标是$(1，1)$"}, {"key": "D", "md": "与y轴交点为(0，2)"}],
            "grading": "wrong", "student_answer": "A"}
# 换了数的同类题：不能当成同一道
PHOTO_OTHER = {**PHOTO_Q1, "number_label": "2", "bbox": [60, 400, 940, 700],
               "stem_md": "已知二次函数 $y=x^2-4x$，下列说法正确的是（　）"}


def test_capture_matches_bank_and_reject(bc):
    _import(bc)
    st = bc.post("/api/students", json={"name": "小测"}).json()
    doc = _capture(bc, st["id"], {"header": "期中", "questions": [PHOTO_Q1, PHOTO_OTHER]})
    items = bc.get(f"/api/documents/{doc}/candidates").json()["items"]
    first, other = items
    assert first["bank"]["paper_title"] == "2025 海淀一模 · 数学" and first["bank"]["number_label"] == "1"
    assert first["bank"]["score"] >= 0.8
    assert first["question"]["answer"] == {"final": "B"} and first["question"]["answer_source"] == "official"
    assert first["kp_codes"] == ["M.FUN.QUAD.GRAPH"]  # 知识点也从题库带过来
    assert other["bank"] is None

    r = bc.post(f"/api/documents/{doc}/confirm", json={"items": [
        {"instance_id": first["instance_id"], "selected": True},
        {"instance_id": other["instance_id"], "selected": False}]}).json()
    assert r["created"] == 1 and r["solving"] == 0  # 有官方答案，不用 AI 解
    m = bc.get(f"/api/mistakes?student_id={st['id']}").json()[0]
    assert m["bank"]["number_label"] == "1" and m["answer_source"] == "official"
    assert bc.post(f"/api/mistakes/{m['id']}/solve").status_code == 400  # 官方答案不让 AI 覆盖

    # 家长说"不是这道题"：取消匹配，恢复原样，交给 AI 解答
    qid = first["question"]["id"]
    r = bc.post(f"/api/questions/{qid}/bank-match", json={"action": "reject"}).json()
    assert r["solving"] is True
    d = bc.get(f"/api/mistakes/{m['id']}").json()
    assert d["bank"] is None and d["question"]["answer_source"] == "ai_unverified"
    # 拒绝过的不会再被自动匹配
    with bc.app_ctx.db.session() as s:
        from app.models import Question
        q = s.get(Question, qid)
        assert not bank.attach_match(bc.app_ctx, s, q)


def test_import_after_capture_backfills_answers(bc):
    st = bc.post("/api/students", json={"name": "小测"}).json()
    doc = _capture(bc, st["id"], {"header": "期中", "questions": [PHOTO_Q1]})
    item = bc.get(f"/api/documents/{doc}/candidates").json()["items"][0]
    bc.post(f"/api/documents/{doc}/confirm", json={"items": [{"instance_id": item["instance_id"], "selected": True}]})
    m = bc.get(f"/api/mistakes?student_id={st['id']}").json()[0]
    assert m["answer_source"] == "ai_unverified" and m["bank"] is None

    p = _import(bc)
    assert p["stats"]["matched_captured"] == 1
    m = bc.get(f"/api/mistakes/{m['id']}").json()
    assert m["bank"]["paper_id"] == p["id"] and m["question"]["answer_source"] == "official"

    # 删除这套卷子：题库的题没了，错题保留已经带过来的答案
    assert bc.delete(f"/api/bank/papers/{p['id']}").status_code == 200
    assert bc.get(f"/api/bank/papers/{p['id']}").status_code == 404
    assert not (bc.app_ctx.settings.data_dir / f"files/bank/{p['id']}").exists()
    m = bc.get(f"/api/mistakes/{m['id']}").json()
    assert m["bank"] is None and m["question"]["answer"] == {"final": "B"}


def test_landscape_pages_are_split_in_halves(bc):
    calls = []

    def fake(task, messages):
        if task == "bank":
            text = messages[-1]["content"][1]["text"]
            right = "右半页" in text
            calls.append(right)
            return {"page_kind": "questions", "questions": [
                {"number_label": "2" if right else "1", "bbox": [0, 100, 1000, 500], "stem_md": f"第{2 if right else 1}题题干"}]}
        return bank_fake(task, messages)

    bc.app_ctx.llm.fake = fake
    p = _import(bc, paper=make_pdf([["A3 横版卷"]], landscape=True), answers=None, verify="false")
    assert calls == [False, True]
    left, right = (q for q in p["questions"])
    with bc.app_ctx.db.session() as s:
        from app.models import BankItem
        assert s.get(BankItem, left["id"]).regions[0]["bbox"] == [0.0, 100.0, 500.0, 500.0]
        assert s.get(BankItem, right["id"]).regions[0]["bbox"] == [500.0, 100.0, 1000.0, 500.0]


# ---------------------------------------------------------------- 纯函数


def test_answers_agree():
    assert bank.answers_agree("B", "选 B", "choice_single") is True
    assert bank.answers_agree("B", "C", "choice_single") is False
    assert bank.answers_agree("ABD", "A、B、D", "choice_multi") is True
    assert bank.answers_agree("变小；变小", "变小，变小", "fill") is True
    assert bank.answers_agree("$\\frac{1}{2}$", "1/2", "fill") is True
    assert bank.answers_agree("$\\sqrt{3}$", "$2\\sqrt{3}$", "fill") is False
    proof = "证 △ABD≌△ACE（SAS），得 AD=AE"
    assert bank.answers_agree(proof, "由等腰三角形两底角相等及 SAS 可得两三角形全等，故 AD 与 AE 相等", "solve") is None
    assert bank.answers_agree("5 A；$3.3\\times10^5$ J", "5A；3.3×10^5J", "calc") is True
    assert bank.answers_agree("60°", "45°", "solve") is False
    assert bank.answers_agree("", "B", "fill") is None


def test_norm_label_and_similarity():
    assert bank.norm_label("27.") == "27" and bank.norm_label("第 8 题") == "8" and bank.norm_label("27(1)") == "27"
    assert bank.norm_label("一、") is None
    a = bank._entry("a", STEM1, OPTS1)
    b = bank._entry("b", PHOTO_Q1["stem_md"], PHOTO_Q1["options"])
    c = bank._entry("c", PHOTO_OTHER["stem_md"], PHOTO_OTHER["options"])
    assert bank.similarity(a, b) >= bank.MATCH_THRESHOLD
    assert bank.similarity(a, c) == 0.0  # 数字不同
    assert bank._entry("d", "求 $x$", None) is None  # 太短，不参与匹配


def test_seg_bbox():
    assert bank._seg_bbox([0, 0, 1000, 1000], 0.5, 1.0, 100, 100) == [500.0, 0.0, 1000.0, 1000.0]
    assert bank._seg_bbox(None, 0.0, 1.0, 100, 100) == [0.0, 0.0, 1000.0, 1000.0]
    assert bank._seg_bbox([200, 400, 1000, 1600], 0.0, 1.0, 2000, 2000) == [100.0, 200.0, 500.0, 800.0]  # 像素坐标


def test_new_columns_added_to_old_database(tmp_path):
    import sqlite3

    path = tmp_path / "old.db"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE questions (id VARCHAR(36) PRIMARY KEY, subject VARCHAR(10) NOT NULL)")
    con.commit()
    con.close()
    db = Database(path)
    cols = [r[1] for r in db.engine.raw_connection().execute("PRAGMA table_info(questions)")]
    assert "bank_match" in cols and "stem_md" in cols


def test_image_page_upload(bc):
    buf = io.BytesIO()
    from PIL import Image
    Image.open(io.BytesIO(synthetic_page())).save(buf, "PNG")

    def fake(task, messages):
        if task == "bank":
            return {"page_kind": "questions", "questions": [
                {"number_label": "1", "bbox": [50, 50, 950, 400], "stem_md": "拍照导入的一道题，题干足够长"}]}
        return bank_fake(task, messages)

    bc.app_ctx.llm.fake = fake
    p = _import(bc, paper=buf.getvalue(), answers=None, verify="false")
    assert p["files"][0]["kind"] == "image" and len(p["questions"]) == 1
    assert bc.get(f"/api/bank/questions/{p['questions'][0]['id']}/image").status_code == 200


# ---------------------------------------------------------------- 答案版卷子（每道题后面紧跟【答案】【解答】）

ANSWER_DOC = make_pdf([
    ["2025-2026学年某校九年级（上）期中数学试卷", "参考答案与试题解析", "一、选择题（每小题2分）",
     "1．（2分）函数 y＝﹣3（x﹣2）2﹣4 的图象的顶点坐标是（ ）", "A．（3，4） B．（﹣2，4） C．（2，4） D．（2，﹣4）",
     "【答案】D", "【解答】解：由顶点式可知顶点坐标为（2，﹣4），", "故选：D．",
     "2．（2分）如图，将△ABC 绕顶点 A 逆时针旋转 30°到△ADE，∠B＝40°，∠DAC＝50°，",
     "则∠E 的度数为（ ）"],
    ["A．40° B．50° C．60° D．70°", "【答案】C", "【解答】解：∠DAE＝80°，∠E＝180°﹣80°﹣40°＝60°，",
     "故选：C．", "二、填空题", "3．（2分）已知 y1＞y2，那么 a 的取值范围是 a＜3 ．", "【答案】a＜3．",
     "【解答】解：二次函数的开口向上……"],
    ["接上题的解答：综上所述，a 的取值范围为 a＜3．", "4．（3分）解方程：x2＝4．", "【答案】x1＝2，x2＝﹣2"],
])


def answer_doc_fake(task: str, messages: list[dict]):
    if task == "bank":
        prompt = messages[-1]["content"][1]["text"]
        ref = prompt.split("<<<")[1].split(">>>")[0]
        if "试题解析" in ref:  # 第 1 页：模型给的框故意偏大，框进了【答案】
            return {"page_kind": "mixed", "header": "某校期中", "questions": [
                {"number_label": "1", "bbox": [40, 100, 960, 400], "question_type": "choice_single",
                 "stem_md": "函数 $y=-3(x-2)^2-4$ 的图象的顶点坐标是（　）", "options": OPT_VERTEX},
                {"number_label": "2", "bbox": [40, 400, 960, 600], "question_type": "choice_single", "has_figure": True,
                 "stem_md": "如图，将 $\\triangle ABC$ 绕顶点 $A$ 逆时针旋转 $30°$ 到 $\\triangle ADE$……则 $\\angle E$ 的度数为（　）"}],
                "answers": [{"number_label": "1", "final_answer": "D", "solution_md": "顶点坐标为 $(2,-4)$"}]}
        if "∠DAE" in ref:
            assert "上一页最后一道题是第 2 题" in prompt
            return {"page_kind": "mixed", "questions": [
                {"number_label": "", "continued": True, "bbox": [40, 0, 960, 200], "options": [{"key": "A", "md": "40°"}]},
                {"number_label": "3", "bbox": [40, 150, 960, 300], "question_type": "fill",
                 "stem_md": "已知 $y_1>y_2$，那么 $a$ 的取值范围是______．"}],
                "answers": [{"number_label": "2", "final_answer": "C", "solution_md": "……"},
                            {"number_label": "3", "final_answer": "$a<3$", "solution_md": "开口向上……"}]}
        # 第 3 页：模型把上一题解答的后半段误报成题目的后半段（第 3 题的答案已经开始了，应该丢掉）
        return {"page_kind": "mixed", "questions": [
            {"number_label": "", "continued": True, "bbox": [40, 0, 960, 120]},
            {"number_label": "4", "bbox": [40, 100, 960, 500], "question_type": "solve", "stem_md": "解方程：$x^2=4$．"}],
            "answers": [{"number_label": "3", "final_answer": "", "solution_md": "综上所述……"},
                        {"number_label": "4", "final_answer": "$x_1=2$，$x_2=-2$", "solution_md": None}]}
    return bank_fake(task, messages)


OPT_VERTEX = [{"key": "A", "md": "$(3,4)$"}, {"key": "B", "md": "$(-2,4)$"}, {"key": "C", "md": "$(2,4)$"},
              {"key": "D", "md": "$(2,-4)$"}]


def test_answer_doc_crops_stop_at_answers(bc):
    from app.adapters import pdf
    from app.models import BankItem

    bc.app_ctx.llm.fake = answer_doc_fake
    p = _import(bc, paper=ANSWER_DOC, answers=None, verify="false")
    assert [pg["kind"] for pg in p["pages"]] == ["mixed", "mixed", "mixed"]
    q1, q2, q3, q4 = p["questions"]
    assert [q["answer"]["final"] for q in (q1, q2, q3, q4)] == ["D", "C", "$a<3$", "$x_1=2$，$x_2=-2$"]
    assert q1["points"] == "2分" and q4["points"] == "3分"  # 分值从文字层读出来
    lay = [pdf.page_layout(ANSWER_DOC, i) for i in range(3)]
    marks = [[ln.y0 for ln in page.lines if ln.text.startswith("【答案】")] for page in lay]
    with bc.app_ctx.db.session() as s:
        r1 = s.get(BankItem, q1["id"]).regions
        r2 = s.get(BankItem, q2["id"]).regions
        r3 = s.get(BankItem, q3["id"]).regions
        r4 = s.get(BankItem, q4["id"]).regions
        flags3 = s.get(BankItem, q3["id"]).flags
    # 模型的框框进了【答案】，按文字层校准后截到【答案】之前
    assert r1[0]["bbox"][3] < marks[0][0] and r1[0]["bbox"][1] < marks[0][0] - 40
    # 第 2 题跨页：第 2 页开头的选项接上，同样截到【答案】之前
    assert [r["page"] for r in r2] == [1, 2] and r2[1]["bbox"][3] < marks[1][0]
    # 第 3 题的答案已经开始了：第 3 页开头误报的"后半段"被丢掉
    assert [r["page"] for r in r3] == [2]
    assert r4[0]["bbox"][3] < marks[2][0]
    # 答案版卷子的填空题：截图里看得到答案
    assert flags3 == {"answer_in_crop": True} and q3["flags"] == {"answer_in_crop": True}
    assert not q1["flags"]


def test_scanned_pdf_falls_back_to_model_boxes(bc):
    """扫描件没有文字层：用模型给的框。"""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 200, 200), False)
    pix.clear_with(255)
    page.insert_image(page.rect, pixmap=pix)

    def fake(task, messages):
        if task == "bank":
            return {"page_kind": "questions", "questions": [
                {"number_label": "1", "bbox": [100, 200, 900, 400], "stem_md": "扫描卷子上的一道题，题干足够长"}]}
        return bank_fake(task, messages)

    bc.app_ctx.llm.fake = fake
    p = _import(bc, paper=doc.tobytes(), answers=None, verify="false")
    from app.models import BankItem
    with bc.app_ctx.db.session() as s:
        assert s.get(BankItem, p["questions"][0]["id"]).regions[0]["bbox"] == [100.0, 200.0, 900.0, 400.0]
