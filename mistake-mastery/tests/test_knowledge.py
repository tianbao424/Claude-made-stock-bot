"""知识点整理：掌握度公式（docs/06 §6）、上级汇总、掌握死角排序、没覆盖到的常考点、接口。"""

import math
from datetime import datetime, timedelta, timezone

import pytest

from app.curriculum import load
from app.models import Attempt, BankItem, BankPaper, Mistake, Question, QuestionKp, Student
from app.services import knowledge

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
CUR = load()


def iso(days_ago: float) -> str:
    return (NOW - timedelta(days=days_ago)).isoformat(timespec="seconds")


def add_mistake(s, sid: str, kps: list[tuple[str, bool]], attempts: list[tuple[str, float]], *, status="TO_REDO",
                difficulty=3, wrong_count=1, round_=1, causes=("CONCEPT",), subject="math") -> Mistake:
    q = Question(subject=subject, origin="captured", content_hash=f"h{len(kps)}{attempts}{status}", stem_md="题",
                 question_type="solve", difficulty=difficulty)
    s.add(q)
    s.flush()
    for code, primary in kps:
        s.add(QuestionKp(question_id=q.id, kp_code=code, is_primary=int(primary)))
    m = Mistake(student_id=sid, question_id=q.id, status=status, round=round_, wrong_count=wrong_count,
                gates={}, error_causes=list(causes), last_wrong_at=iso(0))
    s.add(m)
    s.flush()
    for result, days in attempts:
        s.add(Attempt(mistake_id=m.id, question_id=q.id, round=1, context="redo", result=result, graded_by="guardian",
                      created_at=iso(days)))
    return m


@pytest.fixture
def ctx(client):
    return client.app_ctx


@pytest.fixture
def sid(ctx):
    with ctx.db.session() as s:
        st = Student(name="小测")
        s.add(st)
        s.flush()
        return st.id


def test_mastery_formula_and_rollup(ctx, sid):
    with ctx.db.session() as s:
        # 一道错题：录入时做错（今天），难度 3 → d = 1.1
        add_mistake(s, sid, [("M.FUN.QUAD.GRAPH", True)], [("wrong", 0)])
        stats = knowledge.compute(s, CUR, sid, "math", now=NOW)
    x = stats["M.FUN.QUAD.GRAPH"]
    assert x.observations == 1
    assert x.mastery == pytest.approx((0 + 2 * 0.5) / (1.1 + 2))
    # 上级知识点汇总同样的观测
    assert stats["M.FUN.QUAD"].mastery == pytest.approx(x.mastery)
    assert stats["M.FUN"].mistakes == x.mistakes
    assert "M.GEO" not in stats  # 没数据的知识点不打分

    with ctx.db.session() as s:
        m = s.query(Mistake).first()
        s.add(Attempt(mistake_id=m.id, question_id=m.question_id, round=1, context="redo", result="correct",
                      graded_by="guardian", created_at=iso(0)))
        s.flush()
        stats = knowledge.compute(s, CUR, sid, "math", now=NOW)
    assert stats["M.FUN.QUAD.GRAPH"].mastery == pytest.approx((1.1 + 1) / (2.2 + 2))


def test_recency_difficulty_and_secondary_weights(ctx, sid):
    with ctx.db.session() as s:
        # 21 天前做对（权重 × 1/e），今天做错；主知识点是全等，次知识点是等腰
        add_mistake(s, sid, [("M.GEO.TRI.CONG", True), ("M.GEO.TRI.ISO", False)],
                    [("correct", 21), ("wrong", 0)], difficulty=5)
        stats = knowledge.compute(s, CUR, sid, "math", now=NOW)
    d = 0.8 + 0.1 * 5
    old, new = d * math.exp(-1), d
    assert stats["M.GEO.TRI.CONG"].mastery == pytest.approx((old + 1) / (old + new + 2))
    sec = 0.5
    assert stats["M.GEO.TRI.ISO"].mastery == pytest.approx((sec * old + 1) / (sec * (old + new) + 2))
    # 共同上级按主知识点的权重算一次，不重复计
    assert stats["M.GEO.TRI"].observations == 2
    assert stats["M.GEO.TRI"].mastery == pytest.approx(stats["M.GEO.TRI.CONG"].mastery)


def test_blind_spots_ranking_and_reasons(ctx, sid):
    with ctx.db.session() as s:
        # 二次函数图象：两道没学透，其中一道顽固、错了 3 次
        add_mistake(s, sid, [("M.FUN.QUAD.GRAPH", True)], [("wrong", 1), ("wrong", 0)], status="STUBBORN",
                    wrong_count=3)
        add_mistake(s, sid, [("M.FUN.QUAD.GRAPH", True)], [("wrong", 2)], causes=("CALC",))
        # 二次根式：一道，已经学透，最近都做对
        add_mistake(s, sid, [("M.NUM.RAD.OPS", True)], [("wrong", 30), ("correct", 3), ("correct", 1),
                                                        ("correct", 0)], status="MASTERED")
        # 圆周角：一道没学透
        add_mistake(s, sid, [("M.GEO.CIRCLE.ANGLE", True)], [("wrong", 0)])
        stats = knowledge.compute(s, CUR, sid, "math", now=NOW)
    spots = knowledge.blind_spots(CUR, "math", stats, {})
    codes = [b["code"] for b in spots]
    assert codes[0] == "M.FUN.QUAD.GRAPH"
    assert "M.GEO.CIRCLE.ANGLE" in codes
    assert "M.NUM.RAD.OPS" not in codes  # 学透了、掌握度也不低
    assert all(not any(k.parent_code == c for k in CUR.kps.values()) for c in codes)  # 只列最细的考点
    top = spots[0]
    assert "2 道未学透" in top["reasons"] and "1 道顽固错题" in top["reasons"] and "1 道反复错" in top["reasons"]
    assert any(r.startswith("主要错因：") for r in top["reasons"])
    assert top["status"] == "weak" and top["path"].startswith("函数")

    untouched = knowledge.untouched(CUR, "math", stats, {})
    assert untouched and all(u["code"] not in stats and u["weight"] >= knowledge.FREQUENT for u in untouched)


def test_api_overview_detail_and_bank(logged_in):
    c = logged_in
    ctx = c.app_ctx
    st = c.post("/api/students", json={"name": "小测"}).json()
    with ctx.db.session() as s:
        m1 = add_mistake(s, st["id"], [("M.FUN.QUAD.GRAPH", True)], [("wrong", 0)])
        add_mistake(s, st["id"], [("P.ELEC.OHM.DYNAMIC", True)], [("wrong", 0)], subject="physics", causes=("P_CIRCUIT",))
        # 题库里两道同类题
        paper = BankPaper(subject="math", title="2025 海淀一模 · 数学", year=2025, exam_kind="yimo", status="ready")
        s.add(paper)
        s.flush()
        for n in (6, 26):
            q = Question(subject="math", origin="bank", content_hash=f"b{n}", stem_md="题库题", question_type="solve")
            s.add(q)
            s.flush()
            s.add(QuestionKp(question_id=q.id, kp_code="M.FUN.QUAD.GRAPH", is_primary=1))
            s.add(BankItem(question_id=q.id, paper_id=paper.id, seq=n, number_label=str(n), regions=[]))
        m1_id = m1.id

    o = c.get(f"/api/knowledge?student_id={st['id']}&subject=math").json()
    assert o["summary"]["points"] == 1 and o["summary"]["weak"] == 1 and o["summary"]["open"] == 1
    assert o["blind_spots"][0]["code"] == "M.FUN.QUAD.GRAPH" and o["blind_spots"][0]["bank"] == 2
    fun = next(n for n in o["tree"] if n["code"] == "M.FUN")
    assert fun["status"] == "weak" and fun["mistakes"] == 1 and fun["bank"] == 2
    geo = next(n for n in o["tree"] if n["code"] == "M.GEO")
    assert geo["status"] == "none" and geo["mistakes"] == 0

    top = c.get(f"/api/knowledge/blind-spots?student_id={st['id']}&limit=3").json()
    assert {b["subject"] for b in top} == {"math", "physics"}

    d = c.get(f"/api/knowledge/M.FUN.QUAD?student_id={st['id']}").json()
    assert d["path"].startswith("函数") and [m["id"] for m in d["mistake_list"]] == [m1_id] and d["mistakes"] == 1
    assert d["causes"][0]["code"] == "CONCEPT" and d["causes"][0]["n"] == 1
    assert len(d["bank_questions"]) == 2 and d["bank_questions"][0]["paper_title"] == "2025 海淀一模 · 数学"
    assert any(ch["code"] == "M.FUN.QUAD.GRAPH" and ch["open"] == 1 for ch in d["children"])

    # 错题本按知识点筛选：含下级，但不会把编码前缀相同的兄弟知识点也算进来
    by_kp = c.get(f"/api/mistakes?student_id={st['id']}&kp=M.FUN.QUAD").json()
    assert [m["id"] for m in by_kp] == [m1_id]
    assert c.get(f"/api/mistakes?student_id={st['id']}&kp=M.FUN.QUA").json() == []

    assert c.get(f"/api/knowledge?student_id={st['id']}&subject=chem").status_code == 400
    assert c.get(f"/api/knowledge/NOPE?student_id={st['id']}").status_code == 404
