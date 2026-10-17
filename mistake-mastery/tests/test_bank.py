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


def test_search_questions(bc):
    p = _import(bc)
    rows = bc.get("/api/bank/questions?subject=math&kp=M.FUN.QUAD").json()  # 含下级
    assert [r["number_label"] for r in rows] == ["1", "2", "3"] and rows[0]["paper_id"] == p["id"] and rows[0]["paper_title"]
    assert [r["number_label"] for r in bc.get("/api/bank/questions?type=fill").json()] == ["3"]
    assert [r["number_label"] for r in bc.get("/api/bank/questions?q=二次函数").json()] == ["1"]
    assert bc.get("/api/bank/questions?subject=physics").json() == []
    assert [r["number_label"] for r in bc.get("/api/bank/questions?slot=math.q8.choice_final").json()] == ["1", "2", "3"]


def test_batch_import_pairs_answer_files_by_name(bc):
    files = [("files", ("【试卷】2025北京某区初三（上）期中数学.pdf", PAPER, "application/pdf")),
             ("files", ("【答案】2025北京某区初三（上）期中数学 .pdf", ANSWERS, "application/pdf")),
             ("files", ("2024 某区一模数学试题.pdf", PAPER, "application/pdf"))]
    r = bc.post("/api/bank/papers/batch", data={"subject": "math", "exam_kind": "midterm", "year": "2025"}, files=files)
    assert r.status_code == 200, r.text
    papers = r.json()["papers"]
    assert [x["title"] for x in papers] == ["2025北京某区初三（上）期中数学", "2024 某区一模数学试题"]
    assert papers[0]["answer_file"] and papers[1]["answer_file"] is None
    for x in papers:
        assert bc.get(f"/api/jobs/{x['job_id']}").json()["status"] == "done"
    a = bc.get(f"/api/bank/papers/{papers[0]['paper_id']}").json()
    assert a["stats"]["official"] == 3 and [f["role"] for f in a["files"]] == ["paper", "answer"]
    b = bc.get(f"/api/bank/papers/{papers[1]['paper_id']}").json()
    assert b["stats"]["official"] == 0 and len(b["files"]) == 1
    assert bank.clean_title("【试卷】2025北京某区期中物理-1016.pdf") == "2025北京某区期中物理-1016"
    # 只传了答案文件
    r = bc.post("/api/bank/papers/batch", data={"subject": "math"}, files=[("files", ("答案.pdf", ANSWERS, "application/pdf"))])
    assert r.status_code == 400


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


def test_change_paper_subject_reclassifies_and_detaches_matches(bc):
    """导入时把物理卷选成了数学：改学科后题目换学科、按原学科分的知识点清掉重分，跨学科对上的错题取消匹配。"""
    p = _import(bc)
    st = bc.post("/api/students", json={"name": "小测"}).json()
    doc = _capture(bc, st["id"], {"header": "期中", "questions": [PHOTO_Q1]})
    item = bc.get(f"/api/documents/{doc}/candidates").json()["items"][0]
    assert item["bank"]["paper_id"] == p["id"]
    bc.post(f"/api/documents/{doc}/confirm", json={"items": [{"instance_id": item["instance_id"], "selected": True}]})
    m = bc.get(f"/api/mistakes?student_id={st['id']}").json()[0]

    # 改名称、年份、考试类型不动学科
    r = bc.patch(f"/api/bank/papers/{p['id']}", json={"title": "改过的名字", "year": 2026, "exam_kind": "midterm"}).json()
    assert (r["title"], r["year"], r["exam_kind"], r["job_id"]) == ("改过的名字", 2026, "midterm", None)

    r = bc.patch(f"/api/bank/papers/{p['id']}", json={"subject": "physics"}).json()
    assert r["subject"] == "physics" and r["job_id"]
    assert bc.get(f"/api/jobs/{r['job_id']}").json()["status"] == "done"
    p2 = bc.get(f"/api/bank/papers/{p['id']}").json()
    assert p2["subject"] == "physics" and p2["stats"]["questions"] == 3
    assert all(q["kp_codes"] == [] and q["bj_slot"] is None for q in p2["questions"])  # 假模型给的是数学编码，物理里对不上
    assert [x["id"] for x in bc.get("/api/bank/papers?subject=physics").json()] == [p["id"]]
    assert bc.get("/api/bank/papers?subject=math").json() == []
    # 数学错题和物理卷子的匹配取消了，答案恢复成匹配前的
    d = bc.get(f"/api/mistakes/{m['id']}").json()
    assert d["bank"] is None and d["question"]["answer_source"] != "official"
    with bc.app_ctx.db.session() as s:
        from app.models import Question
        assert s.get(Question, d["question"]["id"]).bank_match is None

    assert bc.patch(f"/api/bank/papers/{p['id']}", json={"subject": "chemistry"}).status_code == 400


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


def test_merge_final_answer_across_pages():
    """解答跨页时同一道题的答案报了两次：不要拼成"(1) y=x-1；(1) y=x-1；(2) …"。"""
    f = bank._merge_final
    assert f("(1) $y=x-1$", "(1) $y=x-1$；(2) $0<a\\le\\frac{1}{3}$") == "(1) $y=x-1$；(2) $0<a\\le\\frac{1}{3}$"
    assert f("(1) 证明见解析；(2) $6\\sqrt{3}$", "（1）$\\triangle BCD\\cong\\triangle BAE$；（2）$6\\sqrt{3}$") == \
        "(1) $\\triangle BCD\\cong\\triangle BAE$；(2) $6\\sqrt{3}$"
    assert f("(1)① $(1,2.25)$", "(1) ① $(1,2.25)$；② $y=-(x-1)^2$；(2) $0\\le h\\le 2$") == "(1) ① $(1,2.25)$；② $y=-(x-1)^2$；(2) $0\\le h\\le 2$"
    assert f("B", "B") == "B" and f("", "C") == "C"
    assert f("20m", "AB=20；距离是20m") == "AB=20；距离是20m"  # 短的被长的包含：取长的
    assert f("20m", "AB=20") == "20m；AB=20"  # 分不出小问、互不包含：照旧拼起来


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
    # 真实物理卷（家长电脑上 DeepSeek 核对）里的答案：分小问逐问比，小问编号和物理量下标不当数值
    agree = bank.answers_agree
    assert agree("(1)1、4；(2)材料；长度；横截面积越大", "(1) 1和4（或4和1）\n(2) 材料；长度；横截面积越大", "experiment")
    assert agree("(1) 5Ω；(2) 6V", "(1) $R_2=5\\Omega$；(2) 电源两端电压 $U=6V$。", "calc") is True
    assert agree("(1)负；排斥；(2)ap；暗", "(1) 负，排斥；(2) cp，亮", "experiment") is False
    assert agree("(1)见图；(2)C；(3)0.5；5", "(1) 电流表串联…… (2) C (3) 0.24，10", "experiment") is False
    assert agree("(1) 正；(2) 放电；(3) 将直流电转换成交流电；(4) 40",
                 "(1) 正；(2) 放电；(3) 将直流电转化为交流电；(4) 40", "reading") is True
    assert agree("(1)L1；断路；(3) 不同规格的灯泡", "(1) L1；断路 (3) 不同规格的小灯泡（若干）", "experiment") is True
    assert agree("见图", "串联电路（电源、开关S1、灯泡L1依次串联）", "solve") is None


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
                {"number_label": "1", "material": True, "bbox": [100, 60, 900, 190], "stem_md": "阅读材料"},
                {"number_label": "1", "bbox": [100, 200, 900, 400], "stem_md": "扫描卷子上的一道题，题干足够长"}]}
        return bank_fake(task, messages)

    bc.app_ctx.llm.fake = fake
    p = _import(bc, paper=doc.tobytes(), answers=None, verify="false")
    from app.models import BankItem
    with bc.app_ctx.db.session() as s:
        regions = s.get(BankItem, p["questions"][0]["id"]).regions
    # 题号前的阅读材料也只能用模型的框，放在题目前面
    assert [r["bbox"] for r in regions] == [[100.0, 60.0, 900.0, 190.0], [100.0, 200.0, 900.0, 400.0]]
    assert p["questions"][0]["stem_md"].startswith("阅读材料")


# ---------------------------------------------------------------- 科普阅读：短文在题号前面，而且跨页

READING_DOC = make_pdf([
    ["2025 某区初三期中 物理", "四、实验探究题", "22. 小明探究串联电路中电压的特点。",
     "阅读下面的说明，回答问题：电源电压保持不变。", "(1) 闭合开关后两灯都不亮，电压表示数为 3V。",
     "五、科普阅读题（共4分）", "请阅读《光伏发电》并回答23题。", "光伏发电",
     "光伏发电是利用半导体界面的光生伏特效应将光能转变为电能的技术。"],
    ["图乙所示为某光伏发电系统结构图，该系统由太阳能电池组件等组成。", "与火力发电相比，光伏发电无污染排放。",
     "23. 根据上述材料，回答下列问题：", "(1) 太阳能电池板的下电极相当于电源的____极。", "六、计算题",
     "24. 电源两端电压保持不变，R1 的阻值为 10Ω。求 R2 的阻值。"],
])


def reading_fake(task: str, messages: list[dict]):
    if task == "bank":
        ref = messages[-1]["content"][1]["text"].split("<<<")[1].split(">>>")[0]
        rough = [40, 30, 960, 970]
        if "实验探究题" in ref:
            return {"page_kind": "questions", "questions": [
                {"number_label": "22", "bbox": rough, "question_type": "experiment", "stem_md": "小明探究串联电路中电压的特点。"},
                {"number_label": "23", "material": True, "bbox": rough, "stem_md": "光伏发电是利用光生伏特效应……"}]}
        # 第 2 页：模型把开头接着的短文误报成上一题（第 22 题）的后半段
        return {"page_kind": "questions", "questions": [
            {"number_label": "", "continued": True, "bbox": rough, "stem_md": "图乙所示为某光伏发电系统结构图……"},
            {"number_label": "23", "bbox": rough, "question_type": "reading", "stem_md": "根据上述材料，回答下列问题："},
            {"number_label": "24", "bbox": rough, "question_type": "calc", "stem_md": "求 $R_2$ 的阻值。"}]}
    return bank_fake(task, messages)


def test_reading_material_before_the_number_goes_with_its_question(bc):
    from app.adapters import pdf
    from app.models import BankItem

    bc.app_ctx.llm.fake = reading_fake
    p = _import(bc, paper=READING_DOC, answers=None, verify="false", subject="physics")
    q22, q23, q24 = p["questions"]
    assert [q["number_label"] for q in (q22, q23, q24)] == ["22", "23", "24"]
    lines = [pdf.page_layout(READING_DOC, i).lines for i in range(2)]

    def ln(page: int, start: str):
        return next(x for x in lines[page] if x.text.replace(" ", "").startswith(start))

    with bc.app_ctx.db.session() as s:
        r22, r23, r24 = (s.get(BankItem, q["id"]).regions for q in (q22, q23, q24))
    # 第 22 题：题目里的"阅读下面的说明……"不算阅读材料；截到"五、科普阅读题"之前，第 2 页开头的短文不接到它后面
    assert [r["page"] for r in r22] == [1]
    assert ln(0, "阅读下面的说明").y1 < r22[0]["bbox"][3] < ln(0, "五、科普阅读").y0
    # 第 23 题：第 1 页从"请阅读……"开始的短文 + 第 2 页开头接着的短文 + 题目本身
    assert [r["page"] for r in r23] == [1, 2, 2]
    assert ln(0, "五、科普阅读").y1 < r23[0]["bbox"][1] <= ln(0, "请阅读《光伏").y0
    assert r23[1]["bbox"][1] <= ln(1, "图乙所示").y0 and r23[1]["bbox"][3] < ln(1, "23.根据").y0
    assert r23[2]["bbox"][1] <= ln(1, "23.根据").y0 and r23[2]["bbox"][3] < ln(1, "六、计算题").y0
    assert q23["stem_md"].startswith("光伏发电是利用光生伏特效应") and "图乙" not in q22["stem_md"]
    assert [r["page"] for r in r24] == [2]


def test_material_line_must_name_the_question():
    m = bank._MATERIAL.match("请阅读《中国的人造太阳》并回答第24～25题。")
    assert m and bank._material_labels(m) == ["24", "25"]
    assert bank._MATERIAL.match("阅读下面的材料，回答问题：") is None  # 题目里面的说明，不是题号前的材料
    assert bank._boundary("请阅读《光伏发电》并回答 24 题。") == "material"


def test_bank_try_tool_writes_report(tmp_path, make_settings, capsys):
    """试导入工具：临时文件夹里跑完整导入，写报告、截图和模型原始输出，不留下数据。"""
    from app.tools import bank_try

    paper, answers = tmp_path / "海淀一模-数学.pdf", tmp_path / "答案.pdf"
    paper.write_bytes(PAPER)
    answers.write_bytes(ANSWERS)
    data = tmp_path / "data"
    data.mkdir()
    out = bank_try.run(paper, answers, "math", tmp_path / "out", settings=make_settings(data), fake=bank_fake)
    report = (out / "report.txt").read_text(encoding="utf-8")
    assert "题目 3 道" in report and "第 2 题  第 1、2 页" in report and "⚠ AI 解出" in report
    assert "没对上题号的答案：['4']" in report
    assert (out / "index.html").read_text(encoding="utf-8").count("<img src='data:image/jpeg;base64,") == 3
    raw = [json.loads(line) for line in (out / "raw.jsonl").read_text(encoding="utf-8").splitlines()]
    assert {r["task"] for r in raw} >= {"bank", "classify", "solve"}
    assert not any(data.iterdir())  # 用的是临时文件夹
    assert bank_try._guess_subject("2025某校初三期中物理.pdf") == "physics"
    assert "AI 返回（bank" in capsys.readouterr().out  # 一边跑一边显示进度


def test_bank_try_ctrl_c_still_writes_report(tmp_path, make_settings):
    """试导入时按 Ctrl+C：停下来，已经拿到的模型输出照样写进报告。"""
    from app.tools import bank_try

    calls = []

    def stop_on_second_page(task: str, messages: list) -> object:
        calls.append(task)
        if len(calls) == 2:
            raise KeyboardInterrupt
        return bank_fake(task, messages)

    paper = tmp_path / "卷子.pdf"
    paper.write_bytes(PAPER)
    data = tmp_path / "data"
    data.mkdir()
    out = bank_try.run(paper, None, "math", tmp_path / "out", settings=make_settings(data), fake=stop_on_second_page)
    assert "Ctrl+C" in (out / "report.txt").read_text(encoding="utf-8")
    assert len((out / "raw.jsonl").read_text(encoding="utf-8").splitlines()) == 1
    from app.jobs import JobHandle
    assert JobHandle.progress.__qualname__ == "JobHandle.progress"  # 打印进度的替身已经还原


def test_continued_part_merges_options_and_joins_broken_sentence():
    """真实模型（家长电脑上的试导入）暴露的三处：跨页题的选项在下一页、句子在页尾断开、只有图的后半段被写了一句说明。"""
    from app.services.bank import _extend

    q = {"stem_md": "用电压表测得 $R_1$ 两", "options": None, "sub_questions": None, "has_figure": False, "regions": []}
    _extend(q, {"stem_md": "端的电压大于 $R_2$ 两端的电压。则下列判断中正确的是",
                "options": [{"key": "A", "md": "甲"}, {"key": "B", "md": "乙"}]}, None)
    assert q["stem_md"] == "用电压表测得 $R_1$ 两端的电压大于 $R_2$ 两端的电压。则下列判断中正确的是"
    assert [o["key"] for o in q["options"]] == ["A", "B"]
    _extend(q, {"stem_md": "（接上一页第 9 题的图：甲为电热水壶，乙为四个电路图）", "has_figure": True,
                "options": [{"key": "B", "md": "乙"}, {"key": "C", "md": "丙"}]}, None)
    assert "接上一页" not in q["stem_md"] and q["has_figure"]  # 模型写的看图说明不是卷面上的字
    assert [o["key"] for o in q["options"]] == ["A", "B", "C"]  # 不重复
    q2 = {"stem_md": "如图所示，求：", "options": None, "sub_questions": None, "has_figure": False, "regions": []}
    _extend(q2, {"stem_md": "(1) 电源电压"}, None)
    assert q2["stem_md"] == "如图所示，求：\n\n(1) 电源电压"  # 说完了的句子、小问另起一段


def test_classify_offers_only_finest_points_and_repairs_codes():
    from app.curriculum import load
    from app.services import prompts

    cur = load()
    text = prompts.classify_messages("physics", cur, [{"id": 0, "stem": "x"}])[1]["content"]
    assert "P.ELEC.OHM.MEASURE" in text and "P.ELEC.OHM  " not in text  # 只列最细的考点
    assert cur.resolve("P.ELEC.OHM.MEASURE", "physics") == "P.ELEC.OHM.MEASURE"
    assert cur.resolve("P.ELEC.OHM.MEAS", "physics") == "P.ELEC.OHM.MEASURE"  # 写短了
    assert cur.resolve("P.ELEC.OHM.XYZ", "physics") == "P.ELEC.OHM"  # 编的：退到上级
    assert cur.resolve("P.ELEC.OHM.CALC", "math") is None and cur.resolve(None, "physics") is None
