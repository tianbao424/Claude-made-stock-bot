"""知识点讲解：材料怎么选、生成与保存、引用编号、又有新错题时提示、重新生成不用缓存。"""

import json
from types import SimpleNamespace

from app.models import SYNCED_MODELS, BankItem, BankPaper, Job, KpLesson, Question, QuestionKp
from app.services import lessons
from tests.test_knowledge import add_mistake

GOOD = {
    "one_line": "看开口、对称轴、顶点，就能从图象读出 $a$、$b$、$c$ 的符号。",
    "key_points": [{"title": "开口方向", "md": "$a>0$ 开口向上，$a<0$ 开口向下。"},
                   {"title": "对称轴", "md": "$x=-\\frac{b}{2a}$，左同右异。"}],
    "method": ["先看开口定 $a$", "再看对称轴定 $b$", "最后看与 $y$ 轴交点定 $c$"],
    "pitfalls": [{"title": "对称轴公式记反", "md": "M1 里把 $-\\frac{b}{2a}$ 写成了 $\\frac{b}{2a}$。", "refs": ["M1", "M9"]}],
    "example": {"ref": "B1", "question_md": "题库题", "steps_md": "一步一步……", "answer": "B"},
    "self_check": ["对称轴的负号写了吗？"],
    "extra": "不在约定里的字段要丢掉",
}


def lesson_fake(seen: list):
    def fake(task, messages):
        assert task == "lesson"
        seen.append(messages)
        return GOOD
    return fake


def _setup(c):
    st = c.post("/api/students", json={"name": "小测", "textbooks": {"math": "bjb"}}).json()
    with c.app_ctx.db.session() as s:
        m_open = add_mistake(s, st["id"], [("M.FUN.QUAD.GRAPH", True)], [("wrong", 3), ("wrong", 0)],
                             status="STUBBORN", wrong_count=2, causes=("CONCEPT",))
        m_done = add_mistake(s, st["id"], [("M.FUN.QUAD.GRAPH", True)], [("wrong", 9), ("correct", 1)],
                             status="MASTERED", causes=("CALC",))
        q = s.get(Question, m_open.question_id)
        q.stem_md, q.answer, q.answer_source = "二次函数 $y=ax^2+bx+c$ 的图象如图……", {"final": "C"}, "ai_unverified"
        paper = BankPaper(subject="math", title="2025 海淀一模 · 数学", year=2025, exam_kind="yimo", status="ready")
        s.add(paper)
        s.flush()
        for n, final in ((8, "B"), (9, None)):  # 第 9 题没有官方答案，不当例题
            bq = Question(subject="math", origin="bank", content_hash=f"b{n}", stem_md=f"题库第 {n} 题",
                          question_type="choice_single", answer={"final": final} if final else None,
                          answer_source="official" if final else "none")
            s.add(bq)
            s.flush()
            s.add(QuestionKp(question_id=bq.id, kp_code="M.FUN.QUAD.GRAPH", is_primary=1))
            s.add(BankItem(question_id=bq.id, paper_id=paper.id, seq=n, number_label=str(n), regions=[]))
        return st["id"], m_open.id, m_done.id


def test_material_puts_open_mistakes_first_and_only_answered_bank(logged_in):
    c = logged_in
    sid, m_open, m_done = _setup(c)
    with c.app_ctx.db.session() as s:
        (subject, kp, situation, mistakes, bank), basis = lessons.gather(c.app_ctx, s, sid, "M.FUN.QUAD")
    assert subject == "math" and kp["textbook"] == "北京版" and kp["path"].startswith("函数")
    assert situation["错题"] == 2 and situation["顽固错题"] == 1 and situation["等级"] in ("薄弱", "待加强")
    # 没学透的（顽固）排在前面，带上正确答案的来源和错因
    assert [m["编号"] for m in mistakes] == ["M1", "M2"]
    assert mistakes[0]["题干"].startswith("二次函数") and mistakes[0]["答案来源"] == "AI 解答 · 待核"
    assert mistakes[0]["错因"] == ["概念不清"] and mistakes[0]["错了几次"] == 2
    assert basis["refs"]["M1"]["id"] == m_open and basis["refs"]["M2"]["id"] == m_done
    # 题库题只用有官方答案的
    assert [b["编号"] for b in bank] == ["B1"] and bank[0]["官方答案"] == "B"
    assert basis["refs"]["B1"]["kind"] == "bank" and basis["refs"]["B1"]["label"] == "2025 海淀一模 · 数学 · 第 8 题"
    assert set(basis["mistake_ids"]) == {m_open, m_done}


def test_generate_save_and_stale(logged_in):
    c = logged_in
    sid, m_open, _ = _setup(c)
    seen: list = []
    c.app_ctx.llm.fake = lesson_fake(seen)
    url = "/api/knowledge/M.FUN.QUAD.GRAPH/lesson"
    assert c.get(f"{url}?student_id={sid}").json() == {"lesson": None, "job": None}

    job_id = c.post(url, json={"student_id": sid}).json()["job_id"]
    assert c.get(f"/api/jobs/{job_id}").json()["status"] == "done"
    prompt = seen[0][-1]["content"]
    assert "二次函数 $y=ax^2+bx+c$" in prompt and "北京版" in prompt and "2025 海淀一模" in prompt

    got = c.get(f"{url}?student_id={sid}").json()
    lesson = got["lesson"]
    assert got["job"] is None and lesson["new_mistakes"] == 0 and lesson["model"] == "fake"
    assert lesson["one_line"].startswith("看开口") and len(lesson["key_points"]) == 2 and len(lesson["method"]) == 3
    assert lesson["pitfalls"][0]["refs"] == ["M1"]  # 材料里没有的 M9 被丢掉
    assert lesson["example"]["ref"] == "B1" and "extra" not in lesson
    assert lesson["refs"]["M1"]["id"] == m_open and lesson["refs"]["B1"]["kind"] == "bank"

    # 首页和知识点页的掌握死角上标出"有讲解"
    spots = c.get(f"/api/knowledge/blind-spots?student_id={sid}").json()
    assert next(b for b in spots if b["code"] == "M.FUN.QUAD.GRAPH")["lesson"] is True

    # 又录入了一道这个知识点的错题：提示可以重新生成
    with c.app_ctx.db.session() as s:
        add_mistake(s, sid, [("M.FUN.QUAD.GRAPH", True)], [("wrong", 0)], causes=("READING",))
    assert c.get(f"{url}?student_id={sid}").json()["lesson"]["new_mistakes"] == 1

    # 重新生成：覆盖原来那份，材料里有了新错题
    c.post(url, json={"student_id": sid, "fresh": True})
    with c.app_ctx.db.session() as s:
        assert s.query(KpLesson).count() == 1
    assert c.get(f"{url}?student_id={sid}").json()["lesson"]["new_mistakes"] == 0
    assert "M3" in seen[-1][-1]["content"]


def test_empty_output_fails_and_duplicate_start(logged_in):
    c = logged_in
    sid, _, _ = _setup(c)
    c.app_ctx.llm.fake = lambda task, messages: {"one_line": "只有一句话"}
    job = c.get(f"/api/jobs/{c.post('/api/knowledge/M.FUN.QUAD.GRAPH/lesson', json={'student_id': sid}).json()['job_id']}").json()
    assert job["status"] == "failed" and "没有写出讲解内容" in job["error"]
    assert c.get(f"/api/knowledge/M.FUN.QUAD.GRAPH/lesson?student_id={sid}").json()["lesson"] is None

    # 已经在生成的，再点一次返回同一个任务
    with c.app_ctx.db.session() as s:
        j = Job(kind="kp_lesson", payload={"student_id": sid, "code": "M.FUN.QUAD.GRAPH"}, status="running")
        s.add(j)
        s.flush()
        running = j.id
    assert c.post("/api/knowledge/M.FUN.QUAD.GRAPH/lesson", json={"student_id": sid}).json()["job_id"] == running
    assert c.get(f"/api/knowledge/M.FUN.QUAD.GRAPH/lesson?student_id={sid}").json()["job"]["id"] == running
    assert c.get(f"/api/knowledge/NOPE/lesson?student_id={sid}").status_code == 404
    assert KpLesson in SYNCED_MODELS  # 生成要花钱：同步到数据仓库


def test_fresh_skips_the_cache(logged_in, monkeypatch):
    llm = logged_in.app_ctx.llm
    llm.fake = None
    calls = []

    def create(**kw):
        calls.append(kw)
        msg = SimpleNamespace(content=json.dumps({"n": len(calls)}))
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)],
                               usage=SimpleNamespace(prompt_tokens=10, completion_tokens=10))

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(llm, "_client", lambda provider: client)
    msgs = [{"role": "user", "content": "同一份材料"}]
    assert llm.chat_json("lesson", msgs, prompt_version="t") == {"n": 1}
    assert llm.chat_json("lesson", msgs, prompt_version="t") == {"n": 1}  # 第二次用缓存
    assert llm.chat_json("lesson", msgs, prompt_version="t", fresh=True) == {"n": 2}
    assert len(calls) == 2
